#!/usr/bin/python

from swift import Swift
import config

from optparse import OptionParser
from sys import argv, exit
from urllib import quote as _quote
import hmac
from hashlib import sha1
from time import time
import os
import sqlite3

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
    '''Lucien class. Encapsulates all the Database work in
       simple function per feature for the player'''

    __gsignals__ = {
        'discovered': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                      (GObject.TYPE_STRING, GObject.TYPE_STRING,
                       GObject.TYPE_STRING, GObject.TYPE_STRING,
                       GObject.TYPE_UINT))
    }

    def __init__(self, command=None):
        GObject.GObject.__init__(self)
        config.read_config_file()
        self.music_list = []

        self.swift = Swift()

        self.dbc = config.prefs['dbc']      # database container
        self.dbo = config.prefs['dbo']   # database object

        if command != "generate-new-db":
            if not self.swift.container_exists(self.dbc):
                exit("There should be a container called '%s'" % self.dbc)

            head, contents = self.swift.get_db_file(self.dbc, self.dbo)
            db = open(self.dbo, "w")
            db.write(contents)
            db.close()

        self.sqlconn = sqlite3.connect(self.dbo)
        with self.sqlconn:
            self.sqlcur = self.sqlconn.cursor()
            self.sqlcur.execute('SELECT SQLITE_VERSION()')

            data = self.sqlcur.fetchone()
            print "SQLite version: %s" % data

    def generate_db(self):
        print "Generating database"
        self.sqlcur.execute("DROP TABLE IF EXISTS Artists")
        self.sqlcur.execute("DROP TABLE IF EXISTS Albums")
        self.sqlcur.execute("DROP TABLE IF EXISTS Tracks")
        self.sqlcur.execute("DROP TABLE IF EXISTS Playlist")
        self.sqlcur.execute("CREATE TABLE Artists " +
                            "(Id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                            "Name TEXT)")
        self.sqlcur.execute("CREATE TABLE Albums " +
                            "(Id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                            "Name TEXT, Artist INT, " +
                            "FOREIGN KEY (Artist) REFERENCES Artists (Id))")
        self.sqlcur.execute("CREATE TABLE Tracks " +
                            "(Id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                            "Title TEXT, Track INT, Uri TEXT, " +
                            "Album INT, " +
                            "FOREIGN KEY (Album) REFERENCES Albums (Id))")
        self.sqlcur.execute("CREATE INDEX ArtistIndex " +
                            "ON Albums (Artist)")
        self.sqlcur.execute("CREATE INDEX AlbumIndex " +
                            "ON Tracks (Album)")
        self.sqlcur.execute("CREATE TABLE Playlist " +
                            "(Id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                            "Track INT, Artist TEXT, Title TEXT, " +
                            "FOREIGN KEY (Track) REFERENCES Tracks (Id))")
        self.sqlconn.commit()

        self.populate_db()

        db_file = open(self.dbo, "r")
        self.swift.update_database_file(self.dbc, self.dbo, db_file)
        db_file.close()

    def populate_db(self, silent=False):
        if not silent:
            print "Music list: \n"
            n = 0

        for t in self.swift.track_list(self.dbc):
            artist, album, title, track_num = t
            self.add_track_to_db(artist, album, title, track_num)

            if not silent:
                print str(n) + ":  " + artist + " / " + album + " / " + title
                n += 1
        self.sqlconn.commit()

    def add_track_to_db(self, artist, album, title, track_num):
        # If Artist exists use it's ID, if not create and get ID
        self.sqlcur.execute('SELECT * FROM Artists WHERE Name = ?',
                            (artist,))
        artist_db = self.sqlcur.fetchall()
        if artist_db:
            artist_id = artist_db[0][0]
        else:
            cur = self.sqlcur.execute('INSERT INTO Artists VALUES(NULL, ?)',
                                      (artist,))
            artist_id = cur.lastrowid

        # If Album exists use it's ID, if not create and get ID
        self.sqlcur.execute('SELECT * FROM Albums WHERE Name = ? AND ' +
                            'Artist = ?', (album, artist_id))
        album_db = self.sqlcur.fetchall()
        if album_db:
            album_id = album_db[0][0]
        else:
            cur = self.sqlcur.execute('INSERT INTO Albums VALUES(NULL, ?, ?)',
                                      (album, artist_id))
            album_id = cur.lastrowid

        uri = "%s/%s" % (album, title)
        self.sqlcur.execute('INSERT INTO Tracks VALUES(NULL, ?, ?, ?, ?)',
                            (title, track_num, uri, album_id))

    def collect_db(self, silent=True):
        self.sqlcur.execute('SELECT * from Tracks ORDER BY Album, Track')
        music = self.sqlcur.fetchall()
        for t in music:
            tid, artist, album, title, track, uri = self.track_complete_data(t)
            self.discovered(artist, album, title, track)

            if not silent:
                print "%s : %s / %s / (%s) %s" % (tid, artist, album, track,
                                                  title)

    def track_complete_data(self, track_row):
        t_id = track_row[0]
        title = track_row[1]
        track_num = track_row[2]
        uri = track_row[3]
        album_id = track_row[4]
        self.sqlcur.execute('SELECT * FROM Albums WHERE Id = ?',
                            (album_id,))
        album_row = self.sqlcur.fetchall()[0]
        album = album_row[1]
        artist_id = album_row[2]
        self.sqlcur.execute('SELECT * FROM Artists WHERE Id = ?',
                            (artist_id,))
        artist_row = self.sqlcur.fetchall()[0]
        artist = artist_row[1]

        return t_id, artist, album, title, track_num, uri

    def play(self, artist, obj_name):
        print "play: %s - %s" % (artist, obj_name)

        # Get a temporary public url
        method = 'GET'
        duration_in_seconds = 60*60*3
        expires = int(time() + duration_in_seconds)
        path = '/v1/AUTH_test/%s/%s' % (artist, obj_name)
        hmac_body = '%s\n%s\n%s' % (method, expires, path)
        sig = hmac.new(self.swift.temp_url_key, hmac_body, sha1).hexdigest()
        s = '{host}{path}?temp_url_sig={sig}&temp_url_expires={expires}'
        url = s.format(host=self.swift.url, path=path, sig=sig,
                       expires=expires)

        return url

    def play_cmd(self, track_num):
        self.sqlcur.execute('SELECT * from Tracks WHERE Id = %s' % track_num)
        track = self.sqlcur.fetchall()[0]
        t_id, artist, album, title, x, y = self.track_complete_data(track)
        obj_name = "%s/%s" % (album, title)
        print self.play(artist, obj_name)

    def add_file(self, filepath, alone=True):
        print "Adding file: " + filepath

        artist, album, title, track_num = self.swift.add_music_file(filepath)
        self.add_track_to_db(artist, album, title, track_num)

        if alone:
            self.sqlconn.commit()
            db_file = open(self.dbo, "r")
            self.swift.update_database_file(self.dbc, self.dbo, db_file)
            db_file.close()

        print "Added"

    def add_folder(self, folderpath):
        print "Adding folder: " + folderpath

        music_files = []
        for media in self.scan_folder_for_ext(folderpath, "mp3"):
            music_files.append(media)
        for media in self.scan_folder_for_ext(folderpath, "ogg"):
            music_files.append(media)
        for media in self.scan_folder_for_ext(folderpath, "oga"):
            music_files.append(media)

        for filepath in music_files:
            self.add_file(filepath, alone=False)

        self.sqlconn.commit()
        db_file = open(self.dbo, "r")
        self.swift.update_database_file(self.dbc, self.dbo, db_file)
        db_file.close()

    def scan_folder_for_ext(self, folder, ext):
        scan = []
        for path, dirs, files in os.walk(folder):
            for file in files:
                if file.split('.')[-1] in ext:
                    location = os.path.join(path, file)
                    scan.append(location)

        return scan

    def discovered(self, artist, album, title, track_num):
        obj_name = "%s/%s" % (album, title)
        self.music_list.append(obj_name)
        self.emit("discovered", obj_name, artist, album, title, track_num)

    def search_in_any(self, query):
        query = "%" + query + "%"
        result = []   # track_info = (id, artist, album, title, track_num, uri)
        self.sqlcur.execute('SELECT * FROM Artists WHERE Name LIKE ?',
                            (query,))
        for artist in self.sqlcur.fetchall():
            artist_name = artist[1]

            self.sqlcur.execute('SELECT * FROM Albums WHERE Artist = ?',
                                (artist[0],))
            for album in self.sqlcur.fetchall():
                album_name = album[1]

                self.sqlcur.execute('SELECT * FROM Tracks WHERE Album = ?',
                                    (album[0],))
                for track in self.sqlcur.fetchall():
                    track_info = (track[0], artist_name, album_name, track[1],
                                  track[2], track[3])
                    result.append(track_info)

        self.sqlcur.execute('SELECT * FROM Albums WHERE Name LIKE ?', (query,))
        for album in self.sqlcur.fetchall():
            self.sqlcur.execute('SELECT * FROM Artists WHERE Id = ?',
                                (album[2],))
            artist_name = self.sqlcur.fetchall()[0][1]
            album_name = album[1]

            self.sqlcur.execute('SELECT * FROM Tracks WHERE Album = ?',
                                (album[0],))
            for track in self.sqlcur.fetchall():
                track_info = (track[0], artist_name, album_name, track[1],
                              track[2], track[3])
                result.append(track_info)

        self.sqlcur.execute('SELECT * FROM Tracks WHERE Title LIKE ?',
                            (query,))
        for track in self.sqlcur.fetchall():
            self.sqlcur.execute('SELECT * FROM Albums WHERE Id = ?',
                                (track[4],))
            album = self.sqlcur.fetchall()[0]
            album_name = album[1]

            self.sqlcur.execute('SELECT * FROM Artists WHERE Id = ?',
                                (album[2],))
            artist_name = self.sqlcur.fetchall()[0][1]

            track_info = (track[0], artist_name, album_name, track[1],
                          track[2], track[3])
            result.append(track_info)

        return result


if __name__ == "__main__":
    parser = OptionParser(usage='''
Positional arguments:
  <subcommand>
    add-file
    add-folder
    generate-new-db
    list
    play
'''.strip('\n') % globals())
    (options, args) = parser.parse_args(argv[1:])

    commands = ('add-file', 'add-folder', 'generate-new-db', 'list', 'play')
    if not args or args[0] not in commands:
        parser.print_usage()
        if args:
            exit('no such command: %s' % args[0])
        exit()

    command = args[0]
    lcn = Lucien(command=command)

    if command == "list":
        lcn.collect_db(silent=False)
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
    if command == "generate-new-db":
        lcn.generate_db()
