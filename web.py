#!/usr/bin/python
# -*- coding: utf-8 -*-
# SuperSonic is a music player using Swift
# Copyright 2014 Luis de Bethencourt

import sqlite3
import os

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

from lucien import Lucien


class SuperSonic(Flask):
    def __init__(self, import_name):
        Flask.__init__(self, import_name)
        self.lucien = Lucien()

# Create app
app = SuperSonic(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'music.db'),
    DEBUG=True,
    SECRET_KEY='sup3r secr3t dev3lopment k3y',
    USERNAME='luisbg',
    PASSWORD='not_2_be_used_y3t!'
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
def show_music():
    db = get_db()
    cur = db.execute('SELECT DISTINCT Artist, Album ' +
                     'FROM Music ORDER BY Artist')
    entries = cur.fetchall()

    return render_template('show_music.html', entries=entries)


@app.route('/album/<artist>/<album>')
def show_album(artist="", album=""):
    db = get_db()
    cur = db.execute('SELECT * FROM Music ' +
                     'WHERE Artist = ? AND Album = ?' +
                     'ORDER BY Track',
                     (artist, album))
    entries = cur.fetchall()

    return render_template('show_album.html', entries=entries, artist=artist,
                           album=album)


@app.route('/play/<idn>')
def play(idn=0):
    db = get_db()
    cur = db.execute('SELECT * FROM Music ' +
                     'WHERE Id = ?',
                     (idn,))
    track = cur.fetchall()[0]
    url = app.lucien.play(track[1], track[5])

    return render_template('play.html', track=track, url=url)


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
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
