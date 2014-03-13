#!/usr/bin/python
# -*- coding: utf-8 -*-
# SuperSonic is a music player using Swift
# Copyright 2014 Luis de Bethencourt

import sqlite3
import os

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, jsonify

from lucien import Lucien


class SuperSonic(Flask):
    def __init__(self, import_name):
        Flask.__init__(self, import_name)
        self.lucien = Lucien()
        self.active = 0
        self.music = {}


# Create app
app = SuperSonic(__name__)
app.config.from_object(__name__)
app.root_path = os.path.dirname(app.root_path)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'music.db'),
    DEBUG=True,
    SECRET_KEY='sup3r secr3t dev3lopment k3y',
    USERNAME='luisbg',
    PASSWORD='le_mr_password'
))
# app.config.from_envvar('SUPERSONIC_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.route('/')
def music():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()

    n = 0
    cur = db.execute('SELECT * FROM Artists ORDER BY Name')
    artist_db = cur.fetchall()
    for art in artist_db:
        artist_id = art[0]
        artist_name = art[1]
        app.music[n] = ("artist", artist_id, artist_name)
        artist_index = n
        n += 1

        cur = db.execute('SELECT * FROM Albums WHERE Artist = ? ' +
                         'ORDER By Name', (artist_id,))
        albums_db = cur.fetchall()
        for alb in albums_db:
            album_id = alb[0]
            album_name = alb[1]
            app.music[n] = ("album", album_id, artist_index, album_name)
            album_index = n
            n += 1

            cur = db.execute('SELECT * FROM Tracks WHERE Album = ? ' +
                             'ORDER BY Track', (album_id,))
            tracks_db = cur.fetchall()
            for trk in tracks_db:
                trk_id = trk[0]
                title = trk[1]
                track_num = trk[2]
                app.music[n] = ("track", trk_id, album_index, track_num,
                                title)
                n += 1

    cur = db.execute('SELECT * FROM Playlist')
    playlist_db = cur.fetchall()

    return render_template('index.html', music=app.music, playlist=playlist_db)


@app.route('/_get_playlist')
def playlist():
    db = get_db()
    cur = db.execute('SELECT * FROM Playlist')
    playlist_db = cur.fetchall()
    playlist = render_template('playlist.html', playlist=playlist_db)

    return jsonify(result=playlist)


@app.route('/_play/<pl_idn>')
def play(pl_idn=0):
    pl_idn = int(pl_idn)
    app.active = pl_idn

    return jsonify(result=True)


@app.route('/_add/<ref>')
def add(ref=""):
    # TODO: Move DB usage to lucien. Make recursive
    tracks_to_add = []    # (idn, artist, title)
    parameters = ref.split("_")
    if parameters[1] == "track":
        idn = parameters[2]

        db = get_db()
        cur = db.execute('SELECT * FROM Tracks WHERE Id = ?', (idn,))
        track = cur.fetchall()[0]
        title = track[1]
        album_id = track[4]

        cur = db.execute('SELECT * FROM Albums WHERE Id = ?', (album_id,))
        artist_id = cur.fetchall()[0][2]
        cur = db.execute('SELECT * FROM Artists WHERE Id = ?', (artist_id,))
        artist = cur.fetchall()[0][1]

        tracks_to_add.append((idn, artist, title))

    if parameters[1] == "album":
        idn = parameters[2]

        db = get_db()
        cur = db.execute('SELECT * FROM Albums WHERE Id = ?', (idn,))
        artist_id = cur.fetchall()[0][2]
        cur = db.execute('SELECT * FROM Artists WHERE Id = ?', (artist_id,))
        artist = cur.fetchall()[0][1]

        cur = db.execute('SELECT * FROM Tracks WHERE Album = ? ORDER BY Track',
                         (idn,))
        tracks = cur.fetchall()
        for t in tracks:
            track_id = t[0]
            title = t[1]
            tracks_to_add.append((track_id, artist, title))

    if parameters[1] == "artist":
        idn = parameters[2]

        db = get_db()
        cur = db.execute('SELECT * FROM Artists WHERE Id = ?', (idn,))
        artist = cur.fetchall()[0][1]

        cur = db.execute('SELECT * FROM Albums WHERE Artist = ?', (idn,))
        albums = cur.fetchall()
        for alb in albums:
            cur = db.execute('SELECT * FROM Tracks WHERE Album = ? ' +
                             'ORDER BY Track', (alb[0],))
            tracks = cur.fetchall()
            for t in tracks:
                track_id = t[0]
                title = t[1]
                tracks_to_add.append((track_id, artist, title))

    for t in tracks_to_add:
        db.execute('INSERT INTO Playlist VALUES(NULL, ?, ?, ?)', (t[0], t[1],
                                                                  t[2]))
    db.commit()
    db.close()

    return jsonify(result="success")


@app.route('/_remove/<idn>')
def remove(idn=0):
    db = get_db()
    db.execute('DELETE FROM Playlist WHERE Id = ?', (idn,))
    db.commit()

    return jsonify(result="success")


@app.route('/_next')
def next():
    db = get_db()
    cur = db.execute('SELECT * FROM Playlist')
    playlist_db = cur.fetchall()

    change = False
    if len(playlist_db) == 0:
        return jsonify(result=change)

    if app.active < (len(playlist_db) - 1):
        app.active += 1
        change = True

    return jsonify(result=change)


@app.route('/_prev')
def prev():
    db = get_db()
    cur = db.execute('SELECT * FROM Playlist')
    playlist_db = cur.fetchall()

    change = False
    if len(playlist_db) == 0:
        return jsonify(result=change)

    if app.active > 0:
        app.active -= 1
        change = True

    return jsonify(result=change)


@app.route('/_get_active')
def get_active():
    db = get_db()
    cur = db.execute('SELECT * FROM Playlist')
    playlist_db = cur.fetchall()
    if len(playlist_db) == 0:
        return jsonify(result=())

    cur = db.execute('SELECT * FROM Tracks WHERE Id = ?',
                     (playlist_db[app.active][1],))
    track = cur.fetchall()[0]
    track_title = track[1]

    cur = db.execute('SELECT * FROM Albums WHERE Id = ?',
                     (track[4],))
    album = cur.fetchall()[0]
    album_name = album[1]

    cur = db.execute('SELECT * FROM Artists WHERE Id = ?',
                     (album[2],))
    artist_name = cur.fetchall()[0][1]

    obj_name = "%s/%s" % (album_name, track_title)
    url = app.lucien.play(artist_name, obj_name)

    res = (artist_name, album_name, track_title, url)
    return jsonify(result=res)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('music'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('music'))


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def run():
    app.debug = True
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    run()
