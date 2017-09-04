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
import zlib
import sqlite3
import threading
import traceback
import collections
import multiprocessing

from collections import defaultdict

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.base_context as base_context
import catsoop.auth as auth
import catsoop.loader as loader
import catsoop.language as language
import catsoop.dispatch as dispatch

from catsoop.process import PKiller, set_pdeathsig
from catsoop.tools.websocket import WebSocket, SimpleWebSocketServer

CHECKER_DB_LOC = os.path.join(base_context.cs_data_root, '__LOGS__', '_checker.db')

PORTNUM = base_context.cs_checker_server_port

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _connect():
    conn = sqlite3.connect(CHECKER_DB_LOC, 60)
    conn.text_factory = str
    conn.row_factory = dict_factory
    return conn, conn.cursor()


def prep_entry(e):
    for i in ('path', 'names', 'form'):
        e[i] = json.loads(e[i])


def exc_message(context):
    exc = traceback.format_exc()
    exc = context['csm_errors'].clear_info(context, exc)
    return ('<p><font color="red">'
            '<b>CAT-SOOP ERROR:</b>'
            '<pre>%s</pre></font>') % exc


def do_check(row):
    os.setpgrp()  # make this part of its own process group
    set_pdeathsig()()  # but make it die if the parent dies.  will this work?

    process = multiprocessing.current_process()
    process._catsoop_check_id = row['magic']

    context = loader.spoof_early_load(row['path'])
    context['cs_course'] = row['path'][0]
    context['cs_path_info'] = row['path']
    context['cs_username'] = row['username']
    context['cs_user_info'] = {'username': row['username']}
    context['cs_user_info'] = auth.get_user_information(context)
    cfile = dispatch.content_file_location(context, row['path'])
    loader.do_late_load(context, context['cs_course'], context['cs_path_info'], context, cfile)

    namemap = collections.OrderedDict()
    for elt in context['cs_problem_spec']:
        if isinstance(elt, tuple):
            m = elt[1]
            namemap[m['csq_name']] = elt

    # start the process killer with the global timeout so we don't run too long
    killer = PKiller(process, context['cs_checker_global_timeout'])
    killer.start()

    # now, depending on the action we want, take the appropriate steps

    names_done = set()
    for name in row['names']:
        if name.startswith('__'):
            name = name[2:].rsplit('_', 1)[0]
        if name in names_done:
            continue
        names_done.add(name)
        question, args = namemap[name]
        if row['action'] == 'submit':
            try:
                resp = question['handle_submission'](row['form'],
                                                     **args)
                score = resp['score']
                msg = resp['msg']
            except:
                resp = {}
                score = 0.0
                msg = exc_message(context)

            score_box = context['csm_tutor'].make_score_display(context, args,
                                                                name, score,
                                                                True)

        elif row['action'] == 'check':
            try:
                msg = question['handle_check'](row['form'], **args)
            except:
                msg = exc_message(context)

            score = None
            score_box = ''

        conn, c = _connect()
        resp = language.handle_custom_tags(context, msg)
        c.execute('UPDATE checker SET progress=2,score=?,score_box=?,response_zipped=? WHERE magic=?',
                  (score, score_box, sqlite3.Binary(zlib.compress(resp.encode(), 9)), row['magic']))
        conn.commit()
        conn.close()

    killer.going = False

running = []

# if anything is in state '1' (running) when we start, that's an error.  turn
# those back to 0's to force them to run again.
conn, c = _connect()
c.execute('UPDATE checker SET progress=0 WHERE progress=1')
conn.commit()
conn.close()

## WEBSOCKET STUFF

# this will map a magic number to a list of connected websockets for that number
all_clients = defaultdict(list)

def send_queued_message(sock, pos):
    sock.sendMessage(json.dumps({'type': 'inqueue', 'position': pos}))


def send_running_message(sock, started):
    sock.sendMessage(json.dumps({'type': 'running', 'started': started, 'now': time.time()}))


def send_done_message(sock, score_box, resp):
    sock.sendMessage(json.dumps({'type': 'newresult',
                                 'score_box': score_box,
                                 'response': zlib.decompress(resp).decode()}))


def send_error_message(sock, score_box, resp):
    send_done_message(sock, score_box, '<font color="red">%s</font>' % resp)


# now let's start up the websocket server
class Reporter(WebSocket):
    def handleMessage(self):
        self.sendMessage(json.dumps({'type': 'hello'}))
        x = json.loads(self.data)
        if x['type'] == 'hello':
            self.magic = m = x['magic']
            all_clients[m].append(self)
            conn, c = _connect()
            c.execute('SELECT * FROM checker WHERE magic=?', (m, ))
            row = c.fetchone()
            if row is not None:
                p = row['progress']
                if p == 0:
                    send_queued_message(self, LASTMAX)
                elif p == 1:
                    send_running_message(self, row['time_started'])
                else:
                    func = send_done_message if p == 2 else send_error_message
                    func(self, row['score_box'], row['response_zipped'])
            conn.close()

    def handleClose(self):
        all_clients[self.magic].remove(self)
        if len(all_clients[self.magic]) == 0:
            del all_clients[self.magic]

LASTMAX = 1
POSITIONS = {}

server = SimpleWebSocketServer('', PORTNUM, Reporter)
reporter = threading.Thread(target=server.serveforever)
reporter.start()

PING = json.dumps({'type': 'ping'})
def keeppingingall():
    while True:
        time.sleep(30)
        for c in all_clients:
            for sock in all_clients[c]:
                sock.sendMessage(PING)
pinger = threading.Thread(target=keeppingingall)
pinger.start()


# and now actually start running
while True:
    # check for dead processes
    dead = set()
    for i in range(len(running)):
        id_, p = running[i]
        if not p.is_alive():
            if p.exitcode < 0:  # this probably only happens if we killed it
                # update the database
                conn, c = _connect()
                resp = "Your submission could not be checked because the checker ran for too long"
                zresp = zlib.compress(resp.encode(), 9)
                c.execute('UPDATE checker SET progress=3,score=0.0,score_box="",response_zipped=? WHERE magic=?',
                          (sqlite3.Binary(zresp), id_))
                conn.commit()
                conn.close()
                # and inform anyone listening
                for i in all_clients[id_]:
                    send_error_message(i, '', zresp)
            else:
                conn2, c2 = _connect()
                c2.execute('SELECT * FROM checker WHERE magic=?', (id_, ))
                row = c2.fetchone()
                if row is not None:
                    for client in all_clients[id_]:
                        send_done_message(client, row['score_box'], row['response_zipped'])
                conn2.close()
            dead.add(i)
    for i in sorted(dead, reverse=True):
        running.pop(i)

    for i in list(all_clients.keys()):
        if len(all_clients[i]) == 0:
            del all_clients[i]

    # if no processes are free, head back to the top of the loop.
    open_slots = base_context.cs_checker_parallel_checks - len(running)

    conn3, c3 = _connect()
    c3.execute('SELECT * FROM checker WHERE progress=0 ORDER BY time ASC')
    rows = c3.fetchall()
    conn3.close()

    pos = 1
    for ix, entry in enumerate(rows):
        prep_entry(entry)
        if ix < open_slots:
            # there's an open slot here.  mark this as being checked
            conn4, c4 = _connect()
            started = time.time()
            c4.execute('UPDATE checker SET progress=1,time_started=? WHERE magic=?',
                      (started, entry['magic']))
            conn4.commit()
            conn4.close()
            # start a worker
            p = multiprocessing.Process(target=do_check, args=(entry, ))
            running.append((entry['magic'], p))
            p.start()
            try:
                del POSITIONS[entry['magic']]
            except:
                pass
            # send an update
            for client in all_clients[entry['magic']]:
                send_running_message(client, started)
        else:
            m = entry['magic']
            if m not in POSITIONS or POSITIONS[m] != pos:
                for client in all_clients[entry['magic']]:
                    send_queued_message(client, pos)
            POSITIONS[m] = pos
            pos += 1
    LASTMAX = pos
    time.sleep(0.1)  # sleep for a little while before the next try
