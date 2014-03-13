#!/usr/bin/python

from optparse import OptionParser
from sys import argv, exit

from src.lucien import Lucien
from src import gtk
from src import web

if __name__ == "__main__":
    parser = OptionParser(usage='''
Positional arguments:
  <subcommand>
    add-file
    add-folder
    generate-new-db
    list
    play
    web
    gtk
'''.strip('\n') % globals())
    (options, args) = parser.parse_args(argv[1:])

    commands = ('add-file', 'add-folder', 'generate-new-db', 'list', 'play',
                'web', 'gtk')
    if not args or args[0] not in commands:
        parser.print_usage()
        if args:
            exit('no such command: %s' % args[0])
        exit()

    command = args[0]

    if command == "web":
        web.run()
        exit()
    if command == "gtk":
        gtk.run()
        exit()

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
