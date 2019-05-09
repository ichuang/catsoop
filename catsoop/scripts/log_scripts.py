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
import ast
import sys
import shlex
import pprint
import shutil
import tempfile
import subprocess

from .. import cslog
from .. import base_context

LOGREAD_USAGE = """\
Print a log in human readable format.

There are two ways to use this command, either:
    catsoop logread FILE

    FILE: a file on disk representing a CAT-SOOP log


or:
    catsoop logread USERNAME PATH LOGNAME

    USERNAME: the name of the user
    PATH: a path from the root, separated by slashes, including the course
          name, e.g. spring19/labs/lab01
    LOGNAME: the name of the log to read (likely either problemstate or
             problemactions)
"""

LOGWRITE_USAGE = """\
Overwrite the given log with the contents of a file.  This operation is
unconditional; not a good idea unless you're sure you want to do it!


There are two ways to use this command, either:
    catsoop logwrite LOGFILE ENTRYFILE

    LOGFILE: a file on disk representing a binary CAT-SOOP log
    ENTRYFILE: a file on disk containing a log in human-readable form, or - to
               read the entry from stdin


or:
    catsoop logread USERNAME PATH LOGNAME ENTRYFILE

    USERNAME: the name of the user
    PATH: a path from the root, separated by slashes, including the course
          name, e.g. spring19/labs/lab01
    LOGNAME: the name of the log to read (likely either problemstate or
             problemactions)
    ENTRYFILE: a file on disk containing a log in human-readable form, or - to
               read the entry from stdin
"""

LOGEDIT_USAGE = """\
Open a log entry for editing in a human readable format.  Changes made
to the file will be written back to the log.  If $EDITOR is set, it will
be used.  Otherwise, we'll try a sensible default (vim, emacs, or nano).
This is a small wrapper around logread and logwrite.

There are two ways to use this command, either:
    catsoop logedit FILE

    FILE: a file on disk representing a CAT-SOOP log


or:
    catsoop logedit USERNAME PATH LOGNAME

    USERNAME: the name of the user
    PATH: a path from the root, separated by slashes, including the course
          name, e.g. spring19/labs/lab01
    LOGNAME: the name of the log to read (likely either problemstate or
             problemactions)
"""


def _find_log(args):
    if len(args) == 1:
        filename = os.path.realpath(args[0])
        base = os.path.join(os.path.realpath(base_context.cs_data_root), "_logs/")
        if not (filename.startswith(base) and filename.endswith(".log")):
            print(
                ("The given file is not a valid log file for this " "installation."),
                file=sys.stderr,
            )
            sys.exit(1)
        fields = filename[len(base) : -4].lstrip("/").split("/")
        if fields[0] != "_courses":
            username = fields[0]
            path = []
        else:
            username = fields[2]
            path = [fields[1]] + fields[3:-1]
        logname = fields[-1]
    else:
        username, path, logname = args
        path = path.split("/") if path else []
    return username, path, logname


def log_read(args):
    if len(args) not in {1, 3} or "-h" in args or "--help" in args:
        print(LOGREAD_USAGE, file=sys.stderr)
        sys.exit(1)
    username, path, logname = _find_log(args)
    entries = cslog.read_log(username, path, logname)
    if not entries:
        print("ERROR: no log entries", file=sys.stderr)
        sys.exit(1)
    for entry in entries:
        pprint.pprint(entry)
        print()


def log_write(args):
    if len(args) not in {2, 4} or "-h" in args or "--help" in args:
        print(LOGWRITE_USAGE, file=sys.stderr)
        sys.exit(1)
    username, path, logname = _find_log(args[:-1])
    entry_file = args[-1]
    if entry_file == "-":
        entries = sys.stdin.read().split("\n\n")
    else:
        with open(entry_file, "r") as f:
            entries = f.read().split("\n\n")
    entries = [ast.literal_eval(e) for e in entries if e]
    for ix, e in enumerate(entries):
        if ix == 0:
            func = cslog.overwrite_log
        else:
            func = cslog.update_log
        func(username, path, logname, e)


def find_editor():
    if "EDITOR" in os.environ:
        return shlex.split(os.environ["EDITOR"])

    for cmd in ("editor", "vim", "emacs", "nano", "vi"):
        ed = shutil.which(cmd)
        if ed:
            return [ed]

    return None


def log_edit(args):
    if len(args) not in {1, 3} or "-h" in args or "--help" in args:
        print(LOGREAD_USAGE, file=sys.stderr)
        sys.exit(1)
    ed = find_editor()
    if ed is None:
        print(
            ("Error: could not find a valid editor.  Please set $EDITOR."),
            file=sys.stderr,
        )
        sys.exit(1)
    username, path, logname = _find_log(args)
    entries = cslog.read_log(username, path, logname)
    body = ""

    with tempfile.NamedTemporaryFile(delete=False, mode="r+") as f:
        # dump entries into the file
        for entry in entries:
            print(pprint.pformat(entry), file=f)
            print(file=f)
        f.flush()

        # open the file for editing
        subprocess.check_call(ed + [f.name])

        # seek to the start of the file, read the entries in
        f.seek(0)
        entries = f.read().split("\n\n")
        entries = [ast.literal_eval(e) for e in entries if e]
        for ix, e in enumerate(entries):
            if ix == 0:
                func = cslog.overwrite_log
            else:
                func = cslog.update_log
            func(username, path, logname, e)


if __name__ == "__main__":
    main()
