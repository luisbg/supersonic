#!/usr/bin/python

from swiftclient import client
import config
from gi.repository import Gst, GstPbutils


class Swift():
    '''Swift class. Encapsulates all the Swift work in
       simple function per feature for the player'''

    def __init__(self, command=None):
        Gst.init(None)  # Move somewhere more particular
        config.read_config_file()

        self.url = config.prefs['url']
        self.authurl = config.prefs['url'] + config.prefs['authurl']
        self.user = config.prefs['user']
        self.key = config.prefs['key']
        self.temp_url_key = config.prefs['temp_url_key']

        self.conn = client.Connection(
            authurl=self.authurl,
            user=self.user,
            key=self.key,
            retries=5,
            auth_version='1.0')
        print "Connection successful to the account: ", self.conn.user

    def container_exists(self, container):
        found = False
        for c in self.conn.get_account()[1]:
            if c['name'] == container:
                found = True
                break

        return found

    def get_db_file(self, dbc, dbo):
        try:
            head = self.conn.head_object(dbc, dbo)
        except:
            print "Database not found"

        head, contents = self.conn.get_object(dbc, dbo)
        return head, contents

    def update_database_file(self, container, obj, db_file):
        self.conn.put_object(container, obj, db_file)

    def track_list(self, dbc):
        tracks = []
        for container in self.conn.get_account()[1]:
            cont_name = container['name']
            if cont_name != dbc:
                items = self.conn.get_container(cont_name)[1]
                for obj in items:
                    head = self.conn.head_object(cont_name, obj['name'])
                    artist = unicode(head['x-object-meta-artist'], "UTF-8")
                    album = unicode(head['x-object-meta-album'], "UTF-8")
                    title = unicode(head['x-object-meta-title'], "UTF-8")
                    track_num = int(head['x-object-meta-track-num'])

                    tracks.append((artist, album, title, track_num))

        return tracks

    def add_music_file(self, filepath):
        contents = open(filepath, "r")

        disc = GstPbutils.Discoverer.new(50000000000)
        file_uri = Gst.filename_to_uri(filepath)
        info = disc.discover_uri(file_uri)
        tags = info.get_tags()
        artist = album = title = "Unknown"
        track_num = 0
        tagged, tag = tags.get_string('artist')
        if tagged:
            artist = unicode(tag, "UTF-8")
        tagged, tag = tags.get_string('album')
        if tagged:
            album = unicode(tag, "UTF-8")
        tagged, tag = tags.get_string('title')
        if tagged:
            title = unicode(tag, "UTF-8")
        tagged, tag = tags.get_uint('track-number')
        if tagged:
            track_num = tag

        headers = []
        headers.append(["X-Object-Meta-Artist", artist])
        headers.append(["X-Object-Meta-Album", album])
        headers.append(["X-Object-Meta-Title", title])
        headers.append(["X-Object-Meta-Track-Num", str(track_num)])

        obj_name = "%s/%s" % (album, title)
        if not self.container_exists(artist):
            self.conn.put_container(artist)
        self.conn.put_object(artist, obj_name, contents, headers=headers)
        contents.close()

        return artist, album, title, track_num
