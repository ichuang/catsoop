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
import time
import atexit
import signal
import sqlite3
import subprocess


os.setpgrp()

scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, '..'))

if base_dir not in sys.path:
    sys.path.append(base_dir)

import catsoop.base_context as base_context
from catsoop.process import set_pdeathsig

procs = (
    (scripts_dir, ['python3', 'checker.py'], 0.1, 'Checker'),
    (scripts_dir, ['python3', 'queue.py'], 0.1, 'Queue'),
    (base_dir, ['uwsgi', '--http', ':%s' % base_context.cs_wsgi_server_port,
                '--wsgi-file', 'wsgi.py',
                '--touch-reload', 'wsgi.py', '-p', str(int(base_context.cs_wsgi_server_processes))], 0.1, 'WSGI Server'),
)

running = []

def check_wsgi_time():
    return os.stat(os.path.join(base_dir, 'wsgi.py')).st_mtime

WSGI_TIME = check_wsgi_time()

# Make sure the checker database is set up

checker_db_loc = os.path.join(base_context.cs_data_root,
                              '__LOGS__',
                              '_checker.db')

checkertable = ('CREATE TABLE IF NOT EXISTS '
                'checker (magic TEXT NOT NULL PRIMARY KEY, '
                'path TEXT NOT NULL, '
                'username TEXT NOT NULL, '
                'names TEXT NOT NULL, '
                'form TEXT NOT NULL, '
                'time REAL NOT NULL, '
                'progress INT NOT NULL, '
                'action TEXT NOT NULL, '
                'score REAL, '
                'score_box TEXT, '
                'response_zipped BLOB, '
                'time_started REAL)')

os.makedirs(os.path.dirname(checker_db_loc), exist_ok=True)
conn = sqlite3.connect(checker_db_loc)
conn.text_factory = str
c = conn.cursor()
c.execute(checkertable)
conn.commit()
conn.close()

# Make sure the queue database is set up

queue_db_loc = os.path.join(base_context.cs_data_root,
                              '__LOGS__',
                              '_queue.db')

queuetable = ('CREATE TABLE IF NOT EXISTS '
              'queues (id TEXT NOT NULL PRIMARY KEY, '
              'username TEXT NOT NULL, '
              'course TEXT NOT NULL, '
              'room TEXT NOT NULL, '
              'type TEXT NOT NULL, '
              'description TEXT NOT NULL, '
              'location TEXT NOT NULL, '
              'started_time REAL NOT NULL, '
              'updated_time REAL NOT NULL, '
              'active INTEGER NOT NULL, '
              'actions TEXT NOT NULL, '
              'claimant TEXT, '
              'photo BLOB, '
              'extra_data TEXT)')


os.makedirs(os.path.dirname(queue_db_loc), exist_ok=True)
conn = sqlite3.connect(queue_db_loc)
conn.text_factory = str
c = conn.cursor()
c.execute(queuetable)
conn.commit()
conn.close()


# Now start the workers.

CHECKER_IX = None

for (ix, (wd, cmd, slp, name)) in enumerate(procs):
    print('Starting', name)
    if 'checker.py' in cmd:
        CHECKER_IX = ix
    killsig = signal.SIGTERM if 'uwsgi' not in cmd else signal.SIGKILL
    running.append(subprocess.Popen(cmd, cwd=wd,
                                    preexec_fn=set_pdeathsig(killsig)))
    time.sleep(slp)

def _kill_children():
    for i in running:
        i.kill()
atexit.register(_kill_children)

while True:
    t = check_wsgi_time()
    if t != WSGI_TIME:
        # if the wsgi.py file changed, reload the checker (uwsgi will reload itself)
        print('wsgi.py changed.  reloading the checker.')
        old_p = running[CHECKER_IX+1]
        old_p.kill()
        old_p.wait()
        wd, cmd, _, _ = procs[CHECKER_IX]
        running[CHECKER_IX] = subprocess.Popen(cmd, cwd=wd,
                                               preexec_fn=set_pdeathsig(signal.SIGTERM))
        WSGI_TIME = t
    time.sleep(1)

