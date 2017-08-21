# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import json
import time
import sqlite3
import threading

from collections import defaultdict

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.api as api
import catsoop.loader as loader
import catsoop.base_context as base_context

from catsoop.tools.websocket import WebSocket, SimpleWebSocketServer

QUEUE_DB_LOC = os.path.join(base_context.cs_data_root,
                            '__LOGS__', '_queue.db')
QUEUE_QUERY = ('SELECT username,type,started_time,updated_time,claimant,'
                      'anonymous_name,description,location '
               'FROM queues WHERE '
               'course=? AND room=? AND active=?')
ROW_QUERY = ('SELECT username,type,started_time,updated_time,claimant,'
                     'anonymous_name,description,location '
             'FROM queues WHERE '
             'course=? AND room=? AND updated_time>?')

PORTNUM = base_context.cs_queue_server_port

#def weird_interleave(l, s):
#    if len(s) > len(l):
#        l, s = s, l
#    r = random.Random()
#    r.seed(l)
#    c = list(l+s)
#    r.shuffle(c)
#    return ''.join(c)
#
#
#def _sha256(x):
#    return base64.b64encode(hashlib.sha256(x.encode()))


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _connect():
    conn = sqlite3.connect(QUEUE_DB_LOC)
    conn.text_factory = str
    conn.row_factory = dict_factory
    return conn, conn.cursor()


## WEBSOCKET STUFF

# CONNECTED maps from (course, room) tuples to a mapping from usernames to a
#           list of active connections for that user/course/room.
CONNECTED = defaultdict(lambda: defaultdict(list))


def prep_row(row, course, room, uname, perms):
    if i['username'] != uname and not perms:
#        i['username'] = _sha256(weird_interleave(uname, SALTS[(course, room, uname)]))
        i['username'] = i['anonymous_name']
        i['anon'] = True
    else:
        i['anon'] = False
    del i['anonymous_name']


def send_updated_message(sock, course, room, uname, rows):
    for i in rows:
        prep_row(i, course, room, uname, sock.perms)
    sock.sendMessage(json.dumps({'type': 'update', 'entries': rows}))


def send_wholequeue_message(sock, course, room, uname):
    msg = {'type': 'queue'}
    conn2, c2 = _connect()
    c2.execute(QUEUE_QUERY, (course, room, 1))
    rows = c2.fetchall()
    conn2.close()
    for i in rows:
        prep_row(i, course, room, uname, sock.perms)
    msg['queue'] = rows
    sock.sendMessage(json.dumps(msg))


# now let's start up the websocket server
class Reporter(WebSocket):
    def handleMessage(self):
        x = json.loads(self.data)
        if x['type'] == 'hello':
            self.api_token = x['api_token']
            g = loader.spoof_early_load([x['course']])
            user_info = api.get_user_information(g, api_token=self.api_token, course=x['course'])
            if not user_info['ok']:
                self.sendMessage({'type': 'hello', 'ok': False,
                                  'msg': 'Bad API Token: <tt>%s</tt>' % self.api_token})
                self.sendClose()
                return
            user_info = user_info['user_info']
            self.sendMessage(json.dumps({'type': 'hello', 'ok': True}))
            self.uname = user_info['username']
            self.course = x['course']
            self.room = x['room']
            self.perms = 'queue_staff' in user_info.get('permissions', [])
            CONNECTED[(self.course, self.room)][self.uname].append(self)
            send_wholequeue_message(self, self.course, self.room, self.uname)

    def handleClose(self):
        # need to remove this person
        mine = CONNECTED[(self.course, self.room)][self.username]
        mine.remove(self)
        if len(mine) == 0:
            del CONNECTED[(self.course, self.room)]


server = SimpleWebSocketServer('', PORTNUM, Reporter)

reporter = threading.Thread(target=server.serveforever)
reporter.start()

# and now actually start running

# The queues themselves are stored in the SQLite database.  We will check
# against the database directly, instead of trying to keep a copy in memory.
# In order to do this, we need to keep track of, for each room, when we last
# looked for an update, and which IDs we were tracking.
LAST_CHECK_TIME = defaultdict((lambda x: lambda: x)(time.time()))

while True:
    # get all the queues we're currently watching (we don't need to care about
    # ones we're not watching).
    print('here', CONNECTED)
    conn, c = _connect()
    for key in list(CONNECTED.keys()):
        course, room = key
        t = time.time()
        c.execute(ROW_QUERY, (course, room, LAST_CHECK_TIME[key]))
        rows = c.fetchall()
        # send all the updates
        if len(rows) > 0:
            for username in CONNECTED[key]:
                for connection in CONNECTED[key][username]:
                    send_updated_message(connection, course, room, username, [dict(i) for i in rows])
        LAST_CHECK_TIME[key] = t
    conn.close()
    time.sleep(0.1)
