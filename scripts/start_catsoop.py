#!/usr/bin/env python3

# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hartz@mit.edu>
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

# Make sure the checker database is set up

checker_db_loc = os.path.join(base_context.cs_data_root,
                              '__LOGS__',
                              '_checker')

for subdir in ('queued', 'running', 'results'):
    os.makedirs(os.path.join(checker_db_loc, subdir), exist_ok=True)


procs = [
    (scripts_dir, [sys.executable, 'checker.py'], 0.1, 'Checker'),
    (scripts_dir, [sys.executable, 'reporter.py'], 0.1, 'Reporter'),
]

# set up WSGI options

if base_context.cs_wsgi_server == 'cheroot':
    wsgi_ports = base_context.cs_wsgi_server_port

    if not isinstance(wsgi_ports, list):
        wsgi_ports = [wsgi_ports]

    for port in wsgi_ports:
        procs.append((scripts_dir,
                      [sys.executable, 'wsgi_server.py', str(port)],
                      0.1,
                      'WSGI Server at Port %d' % port))
elif base_context.cs_wsgi_server == 'uwsgi':
    if base_context.cs_wsgi_server_min_processes >= base_context.cs_wsgi_server_max_processes:
        uwsgi_opts = ['--processes', str(base_context.cs_wsgi_server_min_processes)]
    else:
        uwsgi_opts = [
            '--cheaper', str(base_context.cs_wsgi_server_min_processes),
            '--workers', str(base_context.cs_wsgi_server_max_processes),
            '--cheaper-step', '1',
            '--cheaper-initial', str(base_context.cs_wsgi_server_min_processes),
        ]

    uwsgi_opts = [
        '--http', ':%s' % base_context.cs_wsgi_server_port,
        '--thunder-lock',
        '--wsgi-file', os.path.join('catsoop', 'wsgi.py'),
        '--touch-reload', os.path.join('catsoop', 'wsgi.py'),
    ] + uwsgi_opts

    procs.append((base_dir, ['uwsgi'] + uwsgi_opts, 0.1, 'WSGI Server'))
else:
    raise ValueError('unsupported wsgi server: %r' % base_context.cs_wsgi_server)

running = []

for (ix, (wd, cmd, slp, name)) in enumerate(procs):
    print('Starting', name)
    running.append(subprocess.Popen(cmd, cwd=wd,
                                    preexec_fn=set_pdeathsig(signal.SIGTERM)))
    time.sleep(slp)

def _kill_children():
    for ix, i in enumerate(running):
        os.kill(i.pid, signal.SIGTERM)
atexit.register(_kill_children)

while True:
    time.sleep(1)
