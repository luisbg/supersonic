#!/usr/bin/python

from swiftclient import client

from optparse import OptionParser
from sys import argv, exit
from urllib import quote as _quote
import hmac
from hashlib import sha1
from time import time

from gi.repository import GObject

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
                       GObject.TYPE_STRING, GObject.TYPE_STRING))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.music_list = []

        self.url = "http://luisbg.dyndns.org:8080"
        self.authurl = self.url + "/auth/v1.0"
        self.user = "test:tester"
        self.key = "testing"
        self.container = "music"
        self.temp_url_key = "b3968d0207b54ece87cccc06515a89d4"

        self.conn = client.Connection(
            authurl = self.authurl,
            user = self.user,
            key = self.key,
            retries = 5,
            auth_version = '1.0')

        print "Connection successful to the account: ", self.conn.user

        found = False
        for cts in self.conn.get_account()[1]:
            if cts['name'] == self.container:
                found = True
        if not found:
            exit("There should be a container called '%s'" % self.container)

    def list (self, silent=False):
        if not silent:
            print "Music list: \n"
        items = self.conn.get_container(self.container)[1]
        if not items:
            print "There is no music"
            return

        n = 0
        for obj in items:
            self.discovered(obj)

            if not silent:
                #print i
                print str(n) + ": " + i.get('name')
                n += 1

    def play (self, track):
        try:
            head = self.conn.head_object(self.container, track)
        except:
            print track + " not found"

        # print "size: " + head['content-length']
        if head['content-type'] == "audio/mpeg":
            print "media file confirmed"

        # Get a temporary public url
        method = 'GET'
        duration_in_seconds = 60*60*3
        expires = int(time() + duration_in_seconds)
        path = '/v1/AUTH_test/%s/%s' % (self.container, track)
        hmac_body = '%s\n%s\n%s' % (method, expires, path)
        sig = hmac.new(self.temp_url_key, hmac_body, sha1).hexdigest()
        s = '{host}{path}?temp_url_sig={sig}&temp_url_expires={expires}'
        url = s.format(host=self.url, path=path, sig=sig, expires=expires)
        print url

        return url

    def play_cmd (self, track_num):
        self.list (silent=True)
        self.play(self.music_list[track_num])

    def add_file (self, filepath):
        print "Add file " + filepath

        contents = open(filepath, "r")
        self.conn.put_object(self.container, filepath, contents)

    def discovered (self, obj):
        name = obj.get('name')
        self.music_list.append(name)
        #self.emit ("discovered", track, artist, album, title)
        self.emit ("discovered", name, "n/a", "n/a", name)

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
