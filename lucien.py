#!/usr/bin/python

from swiftclient import client

from optparse import OptionParser
from sys import argv, exit
from urllib import quote as _quote
import hmac
from hashlib import sha1
from time import time
import os

from gi.repository import GObject
from gi.repository import Gst, GstPbutils


def encode_utf8(value):
    if isinstance(value, unicode):
        value = value.encode('utf8')
    return value

def quote(value, safe='/'):
    """
    Patched version of urllib.quote that encodes utf8 strings before quoting
    """
    value = encode_utf8(value)
    if isinstance(value, str):
        return _quote(value, safe)
    else:
        return value

class Lucien(GObject.GObject):
    '''Lucien class. Encapsulates all the Swift work in
       simple function per feature for the player'''

    __gsignals__ = {
        'discovered': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                      (GObject.TYPE_STRING, GObject.TYPE_STRING, \
                       GObject.TYPE_STRING, GObject.TYPE_STRING, \
                       GObject.TYPE_UINT))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init(None)  # Move somewhere more particular
        self.music_list = []

        self.url = "http://luisbg.dyndns.org:8080"
        self.authurl = self.url + "/auth/v1.0"
        self.user = "test:tester"
        self.key = "testing"
        self.temp_url_key = "b3968d0207b54ece87cccc06515a89d4"

        self.conn = client.Connection(
            authurl = self.authurl,
            user = self.user,
            key = self.key,
            retries = 5,
            auth_version = '1.0')

        print "Connection successful to the account: ", self.conn.user

    def list (self, silent=False):
        if not silent:
            print "Music list: \n"

        n = 0
        for container in self.conn.get_account()[1]:
            cont_name = container['name']
            items = self.conn.get_container(cont_name)[1]
            for obj in items:
                self.discovered(cont_name, obj)

                if not silent:
                    print str(n) + ": " + cont_name + " - "  + obj.get('name')
                    n += 1

    def play (self, artist, track):
        print "play: %s - %s" % (artist, track)
        try:
            head = self.conn.head_object(artist, track)
        except:
            print track + " not found"

        # print "size: " + head['content-length']
        if head['content-type'] == "audio/mpeg":
            print "media file confirmed"

        # Get a temporary public url
        method = 'GET'
        duration_in_seconds = 60*60*3
        expires = int(time() + duration_in_seconds)
        path = '/v1/AUTH_test/%s/%s' % (artist, track)
        hmac_body = '%s\n%s\n%s' % (method, expires, path)
        sig = hmac.new(self.temp_url_key, hmac_body, sha1).hexdigest()
        s = '{host}{path}?temp_url_sig={sig}&temp_url_expires={expires}'
        url = s.format(host=self.url, path=path, sig=sig, expires=expires)

        return url

    def play_cmd (self, track_num):
        self.list (silent=True)
        print self.play(self.music_list[track_num])

    def add_file (self, filepath):
        print "Add file: " + filepath

        contents = open(filepath, "r")

        disc = GstPbutils.Discoverer.new (50000000000)
        file_uri= Gst.filename_to_uri (filepath)
        info = disc.discover_uri (file_uri)
        tags = info.get_tags ()
        artist = album = title = "Unknown"
        track_num = 0
        tagged, tag = tags.get_string('artist')
        if tagged:
            artist = tag
        tagged, tag = tags.get_string('album')
        if tagged:
            album = tag
        tagged, tag = tags.get_string('title')
        if tagged:
            title = tag
        tagged, tag = tags.get_uint('track-number')
        if tagged:
            track_num = tag

        headers = []
        headers.append(["X-Object-Meta-Artist", artist])
        headers.append(["X-Object-Meta-Album", album])
        headers.append(["X-Object-Meta-Title", title])
        headers.append(["X-Object-Meta-Track-Num", str(track_num)])

        obj_name = "%s/%s" % (album, title)
        if not self.container_exists (artist):
            self.conn.put_container(artist)
        self.conn.put_object(artist, obj_name, contents, headers=headers)
        print "added: %s :: %s \n" % (artist, obj_name)

    def add_folder (self, folderpath):
        print "Adding folder: " + folderpath

        music_files = []
        for media in self.scan_folder_for_ext (folderpath, "mp3"):
            music_files.append(media)
        for media in self.scan_folder_for_ext (folderpath, "ogg"):
            music_files.append(media)
        for media in self.scan_folder_for_ext (folderpath, "oga"):
            music_files.append(media)

        for filepath in music_files:
            self.add_file (filepath)

    def container_exists (self, container):
        found = False
        for c in self.conn.get_account()[1]:
            if c['name'] == container:
                found = True
                break

        return found

    def scan_folder_for_ext (self, folder, ext):
        scan = []
        for path, dirs, files in os.walk (folder):
            for file in files:
                if file.split('.')[-1] in ext:
                    location = os.path.join(path, file)
                    scan.append(location)

        return scan

    def discovered (self, container, obj):
        obj_name = obj.get('name')
        self.music_list.append(obj_name)

        head = self.conn.head_object(container, obj_name)
        artist = album = title = "Unknown"
        track_num = 0
        if 'x-object-meta-artist' in head:
            artist = head['x-object-meta-artist']
        if 'x-object-meta-album' in head:
            album = head['x-object-meta-album']
        if 'x-object-meta-title' in head:
            title = head['x-object-meta-title']
        if 'x-object-meta-track-num' in head:
            track_num = int(head['x-object-meta-track-num'])

        self.emit ("discovered", obj_name, artist, album, title, track_num)

    def search_in_any (self, query):
        result = []
        for track in self.music_list:
            if query.lower() in track[1].lower() or \
                    query.lower() in track[2].lower() or \
                    query.lower() in track[3].lower():
                result.append(track)
        return result


if __name__ == "__main__":
    parser = OptionParser(usage='''
Positional arguments:
  <subcommand>
    add-file
    add-folder
    list
    play
'''.strip('\n') % globals())
    (options, args) = parser.parse_args(argv[1:])

    commands = ('add-file', 'add-folder', 'list', 'play')
    if not args or args[0] not in commands:
        parser.print_usage()
        if args:
            exit('no such command: %s' % args[0])
        exit()

    lcn = Lucien()

    command = args[0]
    if command == "list":
        lcn.list()
    if command == "play":
        if len(args) > 1:
            lcn.play_cmd(int(args[1]))
        else:
            print "Play command needs an argument"
    if command == "add-file":
        if len(args) > 1:
            lcn.add_file(args[1])
        else:
            print "Add-file command needs an argument"
    if command == "add-folder":
        if len(args) > 1:
            lcn.add_folder(args[1])
        else:
            print "Add-folder command needs an argument"
