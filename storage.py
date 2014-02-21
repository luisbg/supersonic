#!/usr/bin/python

from swiftclient import client

from optparse import OptionParser
from sys import argv, exit
from urllib import quote as _quote


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

class Storage():
    def __init__(self):
        self.url = "http://192.168.1.3:8080"
        self.authurl = self.url + "/auth/v1.0"
        self.user = "test:tester"
        self.container = "music"

        self.conn = client.Connection(
            authurl = self.authurl,
            user = self.user,
            key = "testing",
            retries = 5,
            auth_version = '1.0')

        print "Connection successful to the account: ", self.conn.user

        found = False
        for cts in self.conn.get_account()[1]:
            if cts['name'] == self.container:
                found = True
        if not found:
            exit("There should be a container called '%s'" % self.container)

    def list (self):
        print "Music list: \n"
        items = self.conn.get_container(self.container)[1]
        if not items:
            print "There is no music"
            return
        for i in items:
            #print i
            print i.get('name')

    def play (self, track):
        try:
            head = self.conn.head_object(self.container, track)
        except:
            print track + " not found"

        print "size: " + head['content-length']
        if head['content-type'] == "audio/mpeg":
            print "media file confirmed"

        parsed, conn =  self.conn.http_conn
        path = '%s/%s/%s' % (parsed.path, quote(self.container), \
                             quote(track))
        method = 'GET'
        headers = {}
        headers['X-Auth-Token'] = self.conn.token
        conn.request(method, path, '', headers)
        resp = conn.getresponse()

        parsed_response = {}
        client.store_response(resp, parsed_response)
        # print parsed_response
        print resp.url


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

    s = Storage()

    command = args[0]
    if command == "list":
        s.list()
    if command == "play":
        if len(args) > 1:
            s.play(args[1])
        else:
            print "Play command needs an argument"
