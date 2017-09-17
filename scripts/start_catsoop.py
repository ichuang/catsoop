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

from datetime import datetime

os.setpgrp()

scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, '..'))

if base_dir not in sys.path:
    sys.path.append(base_dir)

import catsoop.base_context as base_context
from catsoop.process import set_pdeathsig

procs = (
    (scripts_dir, ['python3', 'checker.py'], 0.1, 'Checker'),
    (scripts_dir, ['python3', 'reporter.py'], 0.1, 'Reporter'),
    (base_dir, ['uwsgi', '--http', ':%s' % base_context.cs_wsgi_server_port,
                '--wsgi-file', 'wsgi.py',
                '-L', '-p', str(int(base_context.cs_wsgi_server_processes))], 0.1, 'WSGI Server'),
)

running = []

# Make sure the checker database is set up

checker_db_loc = os.path.join(base_context.cs_data_root,
                              '__LOGS__',
                              '_checker')

for subdir in ('queued', 'running', 'results'):
    os.makedirs(os.path.join(checker_db_loc, subdir), exist_ok=True)

# Now start the workers.

KILLSIGS = []

for (ix, (wd, cmd, slp, name)) in enumerate(procs):
    print('Starting', name)
    killsig = signal.SIGTERM if 'uwsgi' not in cmd else signal.SIGKILL
    KILLSIGS.append(killsig)
    running.append(subprocess.Popen(cmd, cwd=wd,
                                    preexec_fn=set_pdeathsig(killsig)))
    time.sleep(slp)

def _kill_children():
    for ix, i in enumerate(running):
        os.kill(i.pid, KILLSIGS[ix])
atexit.register(_kill_children)

while True:
    time.sleep(1)
