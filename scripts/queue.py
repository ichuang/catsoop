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

import catsoop.base_context as base_context

if base_context.cs_queue_websocket is None:
    print('Nevermind.  Queue not wanted.  Dying.')
else:
    import catsoop.api as api
    import catsoop.loader as loader

    from catsoop.tools.websocket import WebSocket, SimpleWebSocketServer

    QUEUE_DB_LOC = os.path.join(base_context.cs_data_root,
                                '__LOGS__', '_queue.db')
    QUEUE_QUERY = ('SELECT id,username,type,started_time,updated_time,claimant,'
                          'description,location,active '
                   'FROM queues WHERE '
                   'course=? AND room=? AND active=? '
                   'ORDER BY updated_time ASC')
    ROW_QUERY = ('SELECT id,username,type,started_time,updated_time,claimant,'
                         'description,location,active '
                 'FROM queues WHERE '
                 'course=? AND room=? AND updated_time>? '
                 'ORDER BY updated_time ASC')

    PORTNUM = base_context.cs_queue_server_port


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

    # most browsers will close websockets that have been inactive for some
    # amount of time.  so we'll start a thread to send a 'ping' to every
    # connection every so often.  there is a way to do this without sending
    # JSON (sending a 'ping' frame instead of a 'message'), but i'm not sure
    # how to do it, and this seems to work for now.  maybe look into it later.
    # note: we shouldn't need any error checking in this thread because
    # everything we're looking at is a defaultdict (so no keyerrors), and the
    # websocket module silently fails on all errors (so no exceptions from
    # trying to send).
    PING = json.dumps({'type': 'ping'})

    def keeppingingall():
        while True:
            time.sleep(30)
            for key in CONNECTED:
                for username in CONNECTED[key]:
                    for sock in CONNECTED[key][username]:
                        sock.sendMessage(PING)


    ## WEBSOCKET STUFF

    # CONNECTED maps from (course, room) tuples to a mapping from usernames to a
    #           list of active connections for that user/course/room.
    CONNECTED = defaultdict(lambda: defaultdict(list))

    # The queues themselves are stored in an SQLite database.  We will check
    # against the database directly and send deltas, instead of trying to keep
    # a copy in memory.  In order to do this, we need to keep track of, for
    # each username for each room, the updated_time of the most recent entry
    # they know about.  Each time through the loop, we'll grab all the entries
    # that _not everyone_ knows about and send them along.  This will minimize
    # the number of connections/queries we have to make each time through the
    # loop, but we can still do some filtering to avoid sending duplicate
    # messages (see below).
    LAST_CHECK_TIME = defaultdict(lambda: defaultdict(lambda: -1))


    def prep_row(row, course, room, uname, perms):
        if row['username'] != uname and not perms:
            row['username'] = row['id']


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
                # when we receive this first message, grab the API token and
                # get the associated user's information.
                self.api_token = x['api_token']
                g = loader.spoof_early_load([x['course']])
                user_info = api.get_user_information(g, api_token=self.api_token, course=x['course'])
                if not user_info['ok']:
                    self.sendMessage(json.dumps({'type': 'hello', 'ok': False,
                                      'msg': 'Bad API Token: <tt>%s</tt>' % self.api_token}))
                    return
                user_info = user_info['user_info']
                self.sendMessage(json.dumps({'type': 'hello', 'ok': True}))
                self.uname = user_info['username']
                self.course = x['course']
                self.room = x['room']
                self.perms = 'queue_staff' in user_info.get('permissions', [])
                send_wholequeue_message(self, self.course, self.room, self.uname)
            elif x['type'] == 'here':
                CONNECTED[(self.course, self.room)][self.uname].append(self)
            elif x['type'] == 'max_time':
                LAST_CHECK_TIME[(self.course, self.room)][self.uname] = x['time']

        def handleClose(self):
            # need to remove this person
            room = CONNECTED[(self.course, self.room)]
            mine = room[self.uname]
            mine.remove(self)
            if len(mine) == 0:
                del room[self.uname]
            if len(room) == 0:
                del CONNECTED[(self.course, self.room)]
            del LAST_CHECK_TIME[(self.course, self.room)][self.uname]


    server = SimpleWebSocketServer('', PORTNUM, Reporter)

    reporter = threading.Thread(target=server.serveforever)
    reporter.start()
    pinger = threading.Thread(target=keeppingingall)
    pinger.start()

    while True:
        # get all the queues we're currently watching (we don't need to care about
        # ones we're not watching).
        conn, c = _connect()
        for key in list(CONNECTED.keys()):
            course, room = key
            # get everything that _not everyone_ knows about
            try:
                check_time = min(LAST_CHECK_TIME[key].values())
            except:
                check_time = -1
            c.execute(ROW_QUERY, (course, room, check_time))
            rows = c.fetchall()
            if len(rows) > 0:
                for username in CONNECTED[key]:
                    # here we filter the entries so that each connection only
                    # gets the updates they haven't already seen.
                    mytime = LAST_CHECK_TIME[(course, room)][username]
                    rows = [i for i in rows if i['updated_time'] > mytime]
                    if len(rows) == 0:
                        continue
                    for connection in CONNECTED[key][username]:
                        # once we have the filtered list, send it to all the
                        # connections associated with this user.  we send a
                        # _copy_ of each row because the rows will get mangled
                        # by anonymization.  also, here we can filter to avoid
                        # sending duplicate messages.
                        send_updated_message(connection, course, room,
                                             username, [dict(i) for i in rows])
        conn.close()
        time.sleep(0.1)
