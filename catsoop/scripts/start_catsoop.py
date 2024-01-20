#!/usr/bin/env python3

# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
import hashlib
import sqlite3
import importlib
import subprocess

from datetime import datetime

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

_pid = os.getpid()


def _log(*args, **kwargs):
    print(f"[start_catsoop.py {_pid}]", *args, **kwargs)


def main(options=[]):
    import catsoop.base_context as base_context

    importlib.reload(base_context)
    import catsoop.loader as loader
    from catsoop.process import set_pdeathsig

    # Make sure the checker database is set up
    checker_db_loc = os.path.join(base_context.cs_data_root, "_logs", "_checker")

    for subdir in ("queued", "running", "results", "staging", "actions"):
        os.makedirs(os.path.join(checker_db_loc, subdir), exist_ok=True)

    if not options:
        options = ["checker", "reporter", "web", "plugins"]

    procs = []
    if "checker" in options:
        procs.append(
            (
                scripts_dir,
                [sys.executable, "checker.py"],
                0.1,
                "checker",
            ),
        )

    if "reporter" in options:
        procs.append((scripts_dir, [sys.executable, "reporter.py"], 0.1, "reporter"))

    # put plugin autostart scripts into the list

    if "plugins" in options:
        ctx = loader.generate_context([])
        for plugin in loader.available_plugins(ctx, course=None):
            script_dir = os.path.join(plugin, "autostart")
            if os.path.isdir(script_dir):
                for script in sorted(os.listdir(script_dir)):
                    if not script.endswith(".py"):
                        continue
                    procs.append(
                        (
                            script_dir,
                            [sys.executable, script],
                            0.1,
                            os.path.join(script_dir, script),
                        )
                    )

    # set up WSGI options

    if "web" in options:
        if base_context.cs_wsgi_server == "cheroot":
            _log("using cheroot for web service")
            wsgi_ports = base_context.cs_wsgi_server_port

            if not isinstance(wsgi_ports, list):
                wsgi_ports = [wsgi_ports]

            for port in wsgi_ports:
                procs.append(
                    (
                        scripts_dir,
                        [sys.executable, "wsgi_server.py", str(port)],
                        0.1,
                        "cheroot WSGI server",
                    )
                )
        elif base_context.cs_wsgi_server == "uwsgi":
            _log("using uWSGI for web service")
            if (
                base_context.cs_wsgi_server_min_processes
                >= base_context.cs_wsgi_server_max_processes
            ):
                uwsgi_opts = [
                    "--processes",
                    str(base_context.cs_wsgi_server_min_processes),
                ]
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

            _max_requests = base_context.cs_wsgi_server_worker_max_requests

            uwsgi_opts = (
                [
                    "--http",
                    ":%s" % base_context.cs_wsgi_server_port,
                    "-b",
                    "65535",
                    "--thunder-lock",
                    "--lazy",
                    "--wsgi-file",
                    "wsgi.py",
                    "--touch-reload",
                    "wsgi.py",
                ]
                + (
                    []
                    if _max_requests is None
                    else ["--max-requests", str(_max_requests)]
                )
                + uwsgi_opts
            )

            uwsgi = os.path.join(
                os.path.dirname(os.path.abspath(sys.executable)), "uwsgi"
            )
            if not (os.path.isfile(uwsgi) and os.access(uwsgi, os.X_OK)):
                uwsgi = "uwsgi"
            procs.append((base_dir, [uwsgi, *uwsgi_opts], 0.1, "uWSGI server"))
        else:
            _log(f"unknown wsgi server {base_context.cs_wsgi_server!r}.  exiting.")
            sys.exit(1)

    running = []

    for ix, (wd, cmd, slp, name) in enumerate(procs):
        running.append(
            subprocess.Popen(
                cmd, cwd=wd, preexec_fn=set_pdeathsig(signal.SIGTERM), env=os.environ
            )
        )
        _log(f"started {name!r} with pid {running[-1].pid}: {cmd}")
        time.sleep(slp)

    def _kill_children():
        for ix, i in enumerate(running):
            os.kill(i.pid, signal.SIGTERM)

    atexit.register(_kill_children)

    while True:
        for idx, (procinfo, proc) in enumerate(
            zip(procs, running)
        ):  # restart running process if it has died
            if proc.poll() is not None:
                (wd, cmd, slp, name) = procinfo
                _log(f"{name}!r (pid {proc.pid}) died.  restarting.")
                running[idx] = subprocess.Popen(
                    cmd, cwd=wd, preexec_fn=set_pdeathsig(signal.SIGTERM)
                )
        time.sleep(1)


def startup_catsoop(config_loc=None, options=[]):
    print(cs_logo)
    if config_loc is None:
        config_loc = os.environ.get(
            "XDG_CONFIG_HOME", os.path.expanduser(os.path.join("~", ".config"))
        )
        config_loc = os.path.abspath(os.path.join(config_loc, "catsoop", "config.py"))
        config_loc = os.environ.get("CATSOOP_CONFIG", config_loc)
    if not os.path.isfile(config_loc):
        print(
            "%s does not exist.  Please configure CAT-SOOP first, either by editing that file manually, or by running setup_catsoop.py"
            % config_loc
        )
        sys.exit(1)
    _log(f"using catsoop configuration specified by {config_loc!r}")
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
    main(options)


if __name__ == "__main__":
    startup_catsoop()
