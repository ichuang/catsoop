#!/usr/bin/env python3

# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
import getpass
import logging
import hashlib
import sqlite3
import subprocess

from datetime import datetime

LOGGER = logging.getLogger("cs")

os.setpgrp()

scripts_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(scripts_dir, ".."))

cs_logo = r"""

\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_

  CAT-SOOP
"""


def main():
    import catsoop.base_context as base_context
    from catsoop.process import set_pdeathsig

    # Make sure the checker database is set up
    checker_db_loc = os.path.join(base_context.cs_data_root, "_logs", "_checker")

    for subdir in ("queued", "running", "results"):
        os.makedirs(os.path.join(checker_db_loc, subdir), exist_ok=True)

    procs = [
        (scripts_dir, [sys.executable, "checker.py"], 0.1, "Checker"),
        (scripts_dir, [sys.executable, "reporter.py"], 0.1, "Reporter"),
    ]

    # set up WSGI options

    if base_context.cs_wsgi_server == "cheroot":
        wsgi_ports = base_context.cs_wsgi_server_port

        if not isinstance(wsgi_ports, list):
            wsgi_ports = [wsgi_ports]

        for port in wsgi_ports:
            procs.append(
                (
                    scripts_dir,
                    [sys.executable, "wsgi_server.py", str(port)],
                    0.1,
                    "WSGI Server at Port %d" % port,
                )
            )
    elif base_context.cs_wsgi_server == "uwsgi":
        if (
            base_context.cs_wsgi_server_min_processes
            >= base_context.cs_wsgi_server_max_processes
        ):
            uwsgi_opts = ["--processes", str(base_context.cs_wsgi_server_min_processes)]
        else:
            uwsgi_opts = [
                "--cheaper",
                str(base_context.cs_wsgi_server_min_processes),
                "--workers",
                str(base_context.cs_wsgi_server_max_processes),
                "--cheaper-step",
                "1",
                "--cheaper-initial",
                str(base_context.cs_wsgi_server_min_processes),
            ]

        uwsgi_opts = [
            "--http",
            ":%s" % base_context.cs_wsgi_server_port,
            "--thunder-lock",
            "--wsgi-file",
            "wsgi.py",
            "--touch-reload",
            "wsgi.py",
        ] + uwsgi_opts

        procs.append((base_dir, ["uwsgi"] + uwsgi_opts, 0.1, "WSGI Server"))
    else:
        raise ValueError("unsupported wsgi server: %r" % base_context.cs_wsgi_server)

    running = []

    for (ix, (wd, cmd, slp, name)) in enumerate(procs):
        print("Starting %s (cmd=%s)" % (name, cmd))
        running.append(
            subprocess.Popen(cmd, cwd=wd, preexec_fn=set_pdeathsig(signal.SIGTERM))
        )
        time.sleep(slp)

    def _kill_children():
        for ix, i in enumerate(running):
            os.kill(i.pid, signal.SIGTERM)

    atexit.register(_kill_children)

    while True:
        time.sleep(1)


def startup_catsoop(config_loc=None):
    print(cs_logo)
    print("Using base_dir=%s" % base_dir)
    config_loc = config_loc or os.path.join(base_dir, "catsoop", "config.py")
    if not os.path.isfile(config_loc):
        print(
            "%s does not exist.  Please configure CAT-SOOP first, either by editing that file manually, or by running setup_catsoop.py"
            % config_loc
        )
        sys.exit(1)
    print("Using catsoop configuration specified by %s" % config_loc)
    os.environ["CATSOOP_CONFIG"] = config_loc

    if base_dir not in sys.path:
        sys.path.append(base_dir)

    _enc_salt_file = os.path.join(os.path.dirname(config_loc), "encryption_salt")
    _enc_hash_file = os.path.join(
        os.path.dirname(config_loc), "encryption_passphrase_hash"
    )
    if os.path.isfile(_enc_salt_file):
        with open(_enc_salt_file, "rb") as f:
            salt = f.read()
        with open(_enc_hash_file, "rb") as f:
            phash = f.read()
        print(
            "CAT-SOOP's logs are encrypted.  Please enter the encryption passphrase below."
        )
        while True:
            pphrase = getpass.getpass("Encryption passphrase: ")
            h = hashlib.pbkdf2_hmac("sha512", pphrase.encode("utf8"), salt, 100000)
            if h == phash:
                os.environ["CATSOOP_PASSPHRASE"] = pphrase
                break
            else:
                print("Passphrase does not match stored hash.  Try again.")
    main()


if __name__ == "__main__":
    startup_catsoop()
