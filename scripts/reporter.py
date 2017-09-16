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
import threading

from collections import defaultdict

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if CATSOOP_LOC not in sys.path:
    sys.path.append(CATSOOP_LOC)

import catsoop.base_context as base_context

from catsoop.cslog import unprep
from catsoop.tools.websocket import WebSocket, SimpleWebSocketServer


CHECKER_DB_LOC = os.path.join(base_context.cs_data_root, '__LOGS__', '_checker')
RUNNING = os.path.join(CHECKER_DB_LOC, 'running')
QUEUED = os.path.join(CHECKER_DB_LOC, 'queued')
RESULTS = os.path.join(CHECKER_DB_LOC, 'results')


PORTNUM = base_context.cs_checker_server_port
ALL_CLIENTS = defaultdict(list)
LAST_STATUS = {}

CURRENT = {
    'queued': [],
    'running': set(),
}


def get_status(magic):
    try:
        s = CURRENT['queued'].index(magic) + 1
    except:
        if magic in CURRENT['running']:
            s = 'running'
        elif os.path.isfile(os.path.join(RESULTS, magic)):
            s = 'results'
        else:
            return
    return s


def report_status(magic):
    s = get_status(magic)
    if s is None or s == LAST_STATUS.get(magic, None) and s != 'results':
        # if the status hasn't changed or there is no status yet, don't send a
        # message.
        return

    msg = None
    if isinstance(s, int):  # this is queued to be checked
        msg = {'type': 'inqueue', 'position': s}
    elif s == 'running':
        start = os.stat(os.path.join(RUNNING, magic)).st_ctime
        msg = {'type': 'running', 'started': start, 'now': time.time()}
    elif s == 'results':
        m = unprep(open(os.path.join(RESULTS, magic), 'rb').read())
        sb = m.get('score_box', '?')
        r = m.get('response', '?')
        msg = {'type': 'newresult', 'score_box': sb, 'response': r}
    if msg is None:
        return

    omsg = json.dumps(msg)
    for c in list(ALL_CLIENTS[magic]):
        try:
            c.sendMessage(omsg)
        except:
            pass
    LAST_STATUS[magic] = s


class Reporter(WebSocket):
    def handleMessage(self):
        self.sendMessage(json.dumps({'type': 'hello'}))
        x = json.loads(self.data)
        if x['type'] == 'hello':
            self.magic = m = x['magic']
            ALL_CLIENTS[m].append(self)

    def handleClose(self):
        try:
            ALL_CLIENTS[self.magic].remove(self)
        except:
            pass


server = SimpleWebSocketServer('', PORTNUM, Reporter)
reporter = threading.Thread(target=server.serveforever)
reporter.start()


PING = json.dumps({'type': 'ping'})
def keeppingingall():
    while True:
        time.sleep(30)
        for c in list(ALL_CLIENTS.keys()):
            for sock in ALL_CLIENTS[c]:
                sock.sendMessage(PING)
pinger = threading.Thread(target=keeppingingall)
pinger.start()


while True:
    for magic in list(ALL_CLIENTS.keys()):
        if len(ALL_CLIENTS[magic]) == 0:
            try:
                del ALL_CLIENTS[magic]
            except:
                pass
    CURRENT['queued'] = [i.split('_')[1] for i in sorted(os.listdir(QUEUED))]
    CURRENT['running'] = {i.name for i in os.scandir(RUNNING)}
    for magic in ALL_CLIENTS:
        report_status(magic)
    time.sleep(0.3)
