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
import ctypes
import signal
import subprocess

import rethinkdb as r

os.setpgrp()

scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, '..'))

if base_dir not in sys.path:
    sys.path.append(base_dir)

import catsoop.base_context as base_context
from catsoop.process import set_pdeathsig

procs = (
    (scripts_dir, ['node', 'checker_reporter.js',
                   str(base_context.cs_websocket_server_port)], 0.1, 'Reporter'),
    (scripts_dir, ['python3', 'checker.py'], 0.1, 'Checker'),
    (base_dir, ['uwsgi', '--http', ':%s' % base_context.cs_wsgi_server_port,
                '--wsgi-file', 'wsgi.py',
                '--touch-reload', 'wsgi.py'], 0.1, 'WSGI Server'),
)

running = []

def check_wsgi_time():
    return os.stat(os.path.join(base_dir, 'wsgi.py')).st_mtime

WSGI_TIME = check_wsgi_time()

if ((not os.path.exists(os.path.join(scripts_dir, 'node_modules', 'rethinkdb'))) or
        (not os.path.exists(os.path.join(scripts_dir, 'node_modules', 'websocket')))):
    print('Node modules are missing.  Please run "npm install websocket rethinkdb" from within the scripts directory.')
    sys.exit(0)

# Start RethinkDB First

print('Starting RethinkDB Server')
running.append(subprocess.Popen(['rethinkdb'], cwd=scripts_dir,
                                preexec_fn=set_pdeathsig(signal.SIGTERM)))

# And give it some time
time.sleep(5)

# Now make sure the database is set up

c = r.connect()
try:
    r.db_create('catsoop').run(c)
except:
    pass
c.close()

c = r.connect(db='catsoop')

tables = r.table_list().run(c)
if 'logs' not in tables:
    r.table_create('logs').run(c)
    r.table('logs').index_create('log', [r.row['username'], r.row['path'], r.row['logname']]).run(c)
    r.table('logs').index_wait('log').run(c)

if 'checker' not in tables:
    r.table_create('checker').run(c)
    r.table('checker').index_create('progress').run(c)
    r.table('checker').index_wait('progress').run(c)
    r.table('checker').index_create('log', [r.row['username'], r.row['path']]).run(c)
    r.table('checker').index_wait('log').run(c)

c.close()

# Finally, start the workers.

CHECKER_IX = None

for (ix, (wd, cmd, slp, name)) in enumerate(procs):
    print('Starting', name)
    if 'checker.py' in cmd:
        CHECKER_IX = ix
    killsig = signal.SIGTERM if 'uwsgi' not in cmd else signal.SIGKILL
    running.append(subprocess.Popen(cmd, cwd=wd,
                                    preexec_fn=set_pdeathsig(killsig)))
    time.sleep(slp)

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

