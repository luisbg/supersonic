#!/usr/bin/python
# -*- coding: utf-8 -*-
# SuperSonic is a very simple audio player demo using media indexing
# Copyright 2014 Jean-François Fortin Tam, Luis de Bethencourt

from engine import Engine
from lucien import Lucien
import constants
import config

from gi.repository import Gtk, Gdk
from gi.repository import Gst
from gi.repository import GObject
from os import path

import random
import os
import sys


class GtkUI():
    def __init__(self):
        self.engine = Engine()
        self.lucien = Lucien()

        self.uri = None
        self.artist = None
        self.is_playing = False
        self._sliderGrabbed = False
        self.loop = False
        self.library = {}

        self.builder = Gtk.Builder()
        self.builder.add_from_file(path.join(path.curdir, "templates/gtk.ui"))
        self.builder.connect_signals(self)

        # Sup dawg, I heard you like black,
        # so I put a dark UI in your car so you can drive through the night.
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        self.main_toolbar = self.builder.get_object("main_toolbar")
        self.main_toolbar.get_style_context().add_class("primary-toolbar")
        self.main_toolbar.set_sensitive(False)

        self.previous_button = self.builder.get_object("previous_button")
        self.play_button = self.builder.get_object("play_button")
        self.next_button = self.builder.get_object("next_button")
        self.time_slider = self.builder.get_object("time_slider")
        self.next_button.set_sensitive(False)
        self.previous_button.set_sensitive(False)

        self._prepare_treeviews()

        self.window = self.builder.get_object("window1")
        self.window.set_icon_name("rhythmbox")
        self.window.maximize()
        self.window.connect("delete-event", self.quit)
        self.window.show_all()

        self.engine.connect("about_to_finish", self._onAboutToFinish)
        self.engine.connect("error", self._onError)
        self.lucien.connect("discovered", self._new_media)

        self.lucien.collect_db(silent=True)

        GObject.timeout_add(500, self._updateSliderPosition)

    """
    UI initialization crack
    """
    def _prepare_treeviews(self):
        self.library_treeview = self.builder.get_object("library_treeview")
        self.playlist_treeview = self.builder.get_object("playlist_treeview")
        self.queue_treeview = self.builder.get_object("queue_treeview")
        # If we enable this, we'll get in trouble in the
        # removeFromQueue method:
        # self.queue_treeview.get_selection().
        # set_mode(Gtk.SelectionMode.MULTIPLE)

        # Only 1 "column" to contain all
        self.library_store = Gtk.TreeStore(str)
        # artist, title, URI, track number
        self.playlist_store = Gtk.ListStore(str, str, str, int)
        # cursor, title, URI
        self.queue_store = Gtk.ListStore(str, str, str, str)
        # To keep track of where the cursor was
        self.queue_current_iter = None

        self.library_treeview.set_model(self.library_store)
        self.playlist_treeview.set_model(self.playlist_store)
        self.queue_treeview.set_model(self.queue_store)

        # Library: only one column, with two visible levels (artist, album)
        column = Gtk.TreeViewColumn()
        column_contents = Gtk.CellRendererText()
        column.pack_start(column_contents, True)
        column.add_attribute(column_contents, "text", 0)
        self.library_treeview.append_column(column)

        # Playlist: two columns in the store (title, URI), but only one shown
        column = Gtk.TreeViewColumn("Title")
        title = Gtk.CellRendererText()
        column.pack_start(title, True)
        column.add_attribute(title, "text", 1)
        self.playlist_treeview.append_column(column)

        # Queue: 3 columns in store, 1 shown for cursor, 1 for the track title
        column = Gtk.TreeViewColumn("Cursor")
        cursor = Gtk.CellRendererText()
        column.pack_start(cursor, True)
        column.add_attribute(cursor, "text", 0)
        self.queue_treeview.append_column(column)
        column = Gtk.TreeViewColumn("Title")
        title = Gtk.CellRendererText()
        column.pack_start(title, True)
        column.add_attribute(title, "text", 3)
        self.queue_treeview.append_column(column)

        # Silly hack to steal the focus from the gtk entry:
        self.library_treeview.grab_focus()

    def _new_media(self, lcn, uri, artist, album, title, track_num):
        self._populate_library(uri, artist, album, title, track_num)

    def _populate_library_from_list(self, new_library):
        self.library_store.clear()
        self.library = {}
        for track in new_library:
            self._populate_library(track[5], track[1], track[2], track[3],
                                   track[4])

    def _populate_library(self, uri, artist, album, title, track_num):
        """
        for track in LIBRARY:
            if artist not already there: add it
            if album not already there: add it as a child of the artist
            add the track
        """
        # A list of tracks (and URIs) in a dic of albums in a dic of artists:
        if artist not in self.library:
            self.library[artist] = {}
            artist_iter = self.library_store.append(None, [artist])
            if album not in self.library[artist]:
                self.library[artist][album] = []
                self.library_store.append(artist_iter, [album])
        else:
            if album not in self.library[artist]:
                column = 0
                artist_iter = self.library_store.get_iter_first()
                while (artist !=
                       self.library_store.get_value(artist_iter, column)) \
                        and (artist is not None):
                    artist_iter = self.library_store.iter_next(artist_iter)

                self.library[artist][album] = []
                self.library_store.append(artist_iter, [album])

        self.library[artist][album].append([artist, title, uri, track_num])

    """
    UI methods and callbacks
    """
    def previous(self, unused_widget=None):
        if self.queue_current_iter is None:
            return False
        prev_iter = self.queue_store.iter_previous(self.queue_current_iter)
        if prev_iter is None:
            return False
        self.artist = self.queue_store.get_value(prev_iter, 1)
        self.uri = self.queue_store.get_value(prev_iter, 2)
        self.engine.stop()
        self.play()
        # remove the ♪ cursor
        self.queue_store.set_value(self.queue_current_iter, 0, "")
        self.queue_store.set_value(prev_iter, 0, "♪")
        self.queue_current_iter = prev_iter
        self.next_button.set_sensitive(True)
        if not self.queue_store.iter_previous(self.queue_current_iter):
            self.previous_button.set_sensitive(False)

    def _play_pause(self, widget):
        """
        Callback for the Play pushbutton
        """
        if widget.props.active:
            self.play()
        else:
            self.pause()

    def next(self, unused_widget=None):
        if self.queue_current_iter is None:
            return False
        next_iter = self.queue_store.iter_next(self.queue_current_iter)
        if next_iter is None:
            return False
        self.artist = self.queue_store.get_value(next_iter, 1)
        self.uri = self.queue_store.get_value(next_iter, 2)
        self.engine.stop()
        self.play()
        # remove the ♪ cursor
        self.queue_store.set_value(self.queue_current_iter, 0, "")
        self.queue_store.set_value(next_iter, 0, "♪")
        self.queue_current_iter = next_iter
        self.previous_button.set_sensitive(True)
        if not self.queue_store.iter_next(self.queue_current_iter):
            self.next_button.set_sensitive(False)

    def _loop_toggled(self, widget):
        """
        Callback for the Loop pushbutton
        """
        if widget.props.active:
            print "Activate portal device"
            self.loop = True
        else:
            print "Deactivate looping"
            self.loop = False

    def shuffle(self, unused_widget=None):
        # Walk through the current queue and create a list out of it
        internal_queue = []
        current_iter = self.queue_store.get_iter_first()
        while current_iter:
            artist = self.queue_store.get_value(current_iter, 1)
            uri = self.queue_store.get_value(current_iter, 2)
            title = self.queue_store.get_value(current_iter, 3)
            # The first item is the playback indicator column, not used here,
            # so None
            internal_queue.append([None, artist, uri, title])
            current_iter = self.queue_store.iter_next(current_iter)
        # Shuffle everything up and then recreate the treeview from it.
        random.shuffle(internal_queue)
        self.queue_store = Gtk.ListStore(str, str, str, str)
        for item in internal_queue:
            self.queue_store.append(item)
        self.queue_treeview.set_model(self.queue_store)
        # If the user shuffles, reset everything and play the first track
        self.queue_current_iter = self.queue_store.get_iter_first()
        self.play_button.set_active(False)
        self.play_button.set_active(True)
        self.previous_button.set_sensitive(False)

    def addToQueue(self, unused_widget=None):
        """
        Add the playlist's selected item to the queue. If no item is selected,
        add them all and let the norse gods sort them out.
        """
        # Warning: this all assumes we only allow single item selections.
        # get_selected will fail to work if we allow multiple selections.
        (treemodel, current_iter) = \
            self.playlist_treeview.get_selection().get_selected()
        column = 0

        def _addIterToQueue(current_iter):
            artist = treemodel.get_value(current_iter, 0)
            title = treemodel.get_value(current_iter, 1)
            uri = treemodel.get_value(current_iter, 2)
            self.queue_store.append([None, artist, uri, title])
            # This will be used for the shuffle function. The first item is for
            # the cursor/playback indicator column, but it's not used here
            if self.queue_current_iter is None:
                self.queue_current_iter = self.queue_store.get_iter_first()

        if current_iter is None:
            current_iter = treemodel.get_iter_first()
            # Loop through iters in the playlist (not queue) until we get False
            while current_iter:
                _addIterToQueue(current_iter)
                current_iter = treemodel.iter_next(current_iter)
        else:
            _addIterToQueue(current_iter)

        self.main_toolbar.set_sensitive(True)
        # Enable "Next" when appending after the currently playing track
        if self.is_playing and \
           self.queue_store.iter_next(self.queue_current_iter):
            self.next_button.set_sensitive(True)

    def clearQueue(self, unused_widget=None):
        # C-style "no messing around with loops, just drop the pointer" tactic
        self.queue_store = Gtk.ListStore(str, str, str, str)
        self.queue_treeview.set_model(self.queue_store)
        self.queue_current_iter = None
        # Stop playback, since we're going to insensitize the UI anyway:
        self.play_button.set_active(False)
        self.main_toolbar.set_sensitive(False)

    def _removeFromQueue(self, widget):
        model, row_iter = self.queue_treeview.get_selection().get_selected()
        if row_iter is None:  # Nothing selected, nothing to remove.
            return

        # SNAFU. The treeview selection gives us a model === self.queue_store,
        # but row_iter with a different reference than self.queue_current_iter,
        # even though they have the exact same values and the exact same model,
        # which segfaults later when trying to play another track! Urgh.
        # We're thus forced to do the comparison manually with the URI values:
        selected_row_is_queue_current_iter = False
        if self.queue_store.get_value(row_iter, 2) == \
                self.queue_store.get_value(self.queue_current_iter, 2):
            # That check is quite naïve and might be incorrect in edge cases
            # where you have duplicates in your queue, but whatever.
            selected_row_is_queue_current_iter = True

        # If the removed item was the current iter, figure out its replacement.
        if selected_row_is_queue_current_iter:
            next_item = self.queue_store.iter_next(row_iter)
            if next_item is not None:
                self.queue_current_iter = next_item
            else:
                prev_item = self.queue_store.iter_previous(row_iter)
                if prev_item is not None:
                    self.queue_current_iter = prev_item
                else:
                    self.queue_current_iter = None
        # Else, do nothing; the previous/next feature will still work, and
        # the list store will be working correctly.
        # In any case, we can now safely remove the item from the list store:
        self.queue_store.remove(row_iter)

    def _searchEntryChanged(self, widget):
        result = self.lucien.search_in_any(widget.get_text())
        self._populate_library_from_list(result)

    def _searchEntryIconRelease(self, widget, unused_icon_position,
                                unused_arg):
        widget.set_text("")

    def _libraryRowSelected(self, treeview):
        """
        When a row is clicked in the library treeview, check if it's an artist
        or album. Depending on the type, query self.library to find the child
        tracks (and URIs), and replace self.playlist_store with a new store
        model containing the results.
        """
        (treemodel, current_iter) = treeview.get_selection().get_selected()
        if current_iter is None:
            # Nothing selected. This happens on startup.
            return
        column = 0
        current_value = self.library_store.get_value(current_iter, column)
        if treemodel.iter_depth(current_iter) is 0:
            # An artist is selected
            tracks = []
            for album in self.library[current_value]:
                for track in self.library[current_value][album]:
                    tracks.append(track)
        else:
            # An album is selected
            temp_iter = treemodel.iter_parent(current_iter)
            artist = self.library_store.get_value(temp_iter, column)
            tracks = self.library[artist][current_value]
        # Don't bother with existing items, scrap the old model and rebuild it
        self.playlist_store = Gtk.ListStore(str, str, str, int)
        tracks.sort(key=lambda tup: tup[2])
        for track in tracks:
            self.playlist_store.append(track)
        self.playlist_treeview.set_model(self.playlist_store)

    def _playlistRowActivated(self, unused_treeview, unused_position,
                              unused_column):
        """
        Allow adding to the queue by double-clicking/activating a playlist item
        """
        self.addToQueue()

    def _queueTreeviewRowActivated(self, treeview, unused_position,
                                   unused_column):
        """
        When a row is activated in the queue treeview, start playback.
        """
        (treemodel, current_iter) = treeview.get_selection().get_selected()
        previous_iter = self.queue_current_iter
        if previous_iter:
            treemodel.set_value(previous_iter, 0, "")  # remove the ♪ cursor
        treemodel.set_value(current_iter, 0, "♪")
        self.queue_current_iter = current_iter
        self.engine.stop()
        self.artist = treemodel.get_value(current_iter, 1)
        self.uri = treemodel.get_value(current_iter, 2)
        self.play()

        self.previous_button.set_sensitive(False)
        self.next_button.set_sensitive(False)
        if self.queue_store.iter_previous(self.queue_current_iter):
            self.previous_button.set_sensitive(True)
        if self.queue_store.iter_next(self.queue_current_iter):
            self.next_button.set_sensitive(True)

    def _sliderMouseEvent(self, widget, event):
        """
        We handle the mouse button clicks and movements (scrubbing) here.
        This is thus called by button-press-event, button-release-event and
        motion-notify-event.

        This is also where seeks are triggered on click.
        """
        if Gtk.get_major_version() >= 3 and Gtk.get_minor_version() < 6:
            # Override the event button to use a middle-click when
            # left-clicking the slider, allowing it to wark directly to the
            # desired position. This behavior has been fixed in GTK 3.6.
            event.button = 2
        if event.type is Gdk.EventType.BUTTON_PRESS:
            self._sliderGrabbed = True
        elif event.type is Gdk.EventType.BUTTON_RELEASE:
            self._sliderGrabbed = False

        if event.type is Gdk.EventType.BUTTON_RELEASE:
            target_percent = widget.get_adjustment().props.value / 100.0
            duration = self.engine.query_duration()
            target_position = target_percent * duration
            self.engine.seek(target_position)

    def _updateSliderPosition(self):
        if self.is_playing and not self._sliderGrabbed:
            pos = self.engine.query_position()
            duration = self.engine.query_duration()
            if not duration == 0:  # GStreamer nonsense, occurring randomly.
                new_slider_pos = pos / float(duration) * 100
                # print "Position is", pos, "and duration is", duration
                # print "\tUpdate slider position to", new_slider_pos
                self.time_slider.get_adjustment().props.value = new_slider_pos

        return True

    def quit(self, unused_window=None, unused_event=None):
        Gtk.main_quit
        sys.exit(0)

    """
    Public playback methods (not callbacks)
    """
    def play(self):
        if self.uri is None:
            # The user clicked play without selecting a track, play the 1st
            self.uri = self.queue_store.get_value(self.queue_current_iter, 2)
            self.queue_store.set_value(self.queue_current_iter, 0, "♪")
            self.artist = self.queue_store.get_value(self.queue_current_iter,
                                                     1)
        temp_url = self.lucien.play(self.artist, self.uri)
        self.engine.play(temp_url)
        print "url: " + temp_url + "\n"

        self.is_playing = True
        self.play_button.props.active = True
        self.time_slider.set_sensitive(True)
        if self.queue_store.iter_next(self.queue_current_iter):
            self.next_button.set_sensitive(True)
        if self.queue_store.iter_previous(self.queue_current_iter):
            self.previous_button.set_sensitive(True)

    def pause(self):
        self.engine.pause()
        self.play_button.props.active = False
        self.is_playing = False

    """
    Engine callbacks
    """
    def _onError(self, arg):
        error_iter = self.queue_current_iter
        self.next()
        self.queue_store.set_value(error_iter, 0, "⚠")

    def _onAboutToFinish(self, arg):
        print "Supersonic: about to finish"
        next_iter = self.queue_store.iter_next(self.queue_current_iter)
        if next_iter is not None:
            print "Song ended, play the next one"
            self.artist = self.queue_store.get_value(next_iter, 1)
            self.uri = self.queue_store.get_value(next_iter, 2)
            temp_url = self.lucien.play(self.artist, self.uri)
            self.engine.play(temp_url)

            # remove the ♪ cursor
            self.queue_store.set_value(self.queue_current_iter, 0, "")
            self.queue_store.set_value(next_iter, 0, "♪")
            self.queue_current_iter = next_iter
            self.previous_button.set_sensitive(True)
            if not self.queue_store.iter_next(self.queue_current_iter):
                self.next_button.set_sensitive(False)

        else:
            print "Playback ended"
            if not self.loop:
                self.play_button.set_active(False)
            else:
                first_iter = self.queue_store.get_iter_first()
                self.artist = self.queue_store.get_value(first_iter, 1)
                self.uri = self.queue_store.get_value(first_iter, 2)
                temp_url = self.lucien.play(self.artist, self.uri)
                self.engine.play(temp_url)
                # remove the ♪ cursor
                self.queue_store.set_value(self.queue_current_iter, 0, "")
                self.queue_store.set_value(first_iter, 0, "♪")
                self.queue_current_iter = first_iter
                self.previous_button.set_sensitive(True)
                if self.queue_store.iter_next(self.queue_current_iter):
                    self.next_button.set_sensitive(True)


def run():
    """Run supersonic"""
    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0700)

    if not os.path.isfile(config._config_path):
        exec_path = os.path.abspath(sys.argv[0])
        base_dir = os.path.dirname(exec_path)
        sample_cfg_path = os.path.join(base_dir, "sample_config")
        if os.path.isfile(sample_cfg_path):
            config.write_config_file(sample_cfg_path)

    ui = GtkUI()
    Gtk.main()


if __name__ == '__main__':
    run()
