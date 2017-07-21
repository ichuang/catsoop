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

os.setpgrp()

scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, '..'))

if base_dir not in sys.path:
    sys.path.append(base_dir)

import catsoop.base_context as base_context

procs = (
    (scripts_dir, ['rethinkdb'], 5, 'RethinkDB Server'),
    (scripts_dir, ['node', 'checker_reporter.js',
                   str(base_context.cs_websocket_server_port)], 0.1, 'Reporter'),
    (scripts_dir, ['python3', 'checker.py'], 0.1, 'Checker'),
    (base_dir, ['uwsgi', '--http', ':%s' % base_context.cs_wsgi_server_port,
                '--wsgi-file', 'wsgi.py',
                '--touch-reload', 'wsgi.py'], 0.1, 'WSGI Server'),
)

running = []

libc = ctypes.CDLL("libc.so.6")
def set_pdeathsig(sig = signal.SIGTERM):
    def callable():
        return libc.prctl(1, sig)
    return callable

for (wd, cmd, slp, name) in procs:
    print('Starting', name)
    running.append(subprocess.Popen(cmd, cwd=wd,
                                    preexec_fn=set_pdeathsig(signal.SIGTERM)))
    time.sleep(slp)

while True:
    time.sleep(10)
