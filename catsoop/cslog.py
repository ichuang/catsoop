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
"""
Logging mechanisms in catsoopdb

From a high-level perspective, CAT-SOOP's logs are sequences of Python objects.

A log is identified by a `db_name` (typically a username), a `path` (a list of
strings starting with a course name), and a `logname` (a string).

On disk, each log is a file containing zipped, pickled Python objects,
separated by a known value that is guaranteed not to exist in any of the
pickled objects.  This is an implementation detail that most people shouldn't
need to worry about.

This module provides functions for interacting with and modifying those logs.
In particular, it provides ways to retrieve the Python objects in a log, or to
add new Python objects to a log.
"""

import os
import re
import zlib
import pickle
import random
import string
import contextlib

_nodoc = {'passthrough', 'FileLock', 'SEP_CHARS', 'create_if_not_exists',
          'get_separator', 'good_separator', 'modify_most_recent'}

@contextlib.contextmanager
def passthrough():
    yield

from . import base_context
from .tools.filelock import FileLock

SEP_CHARS = (string.ascii_letters + string.digits).encode()


def good_separator(sep, data, new=None):
    return sep not in data and (new is None or sep not in new)


def get_separator(data, new=None):
    out = None
    while out is None or not good_separator(out, data, new=new):
        out = bytes(random.choice(SEP_CHARS) for i in range(20))
    return out


def create_if_not_exists(directory):
    os.makedirs(directory, exist_ok=True)


def prep(x):
    """
    Helper function to pickle and compress a Python object.
    """
    return zlib.compress(pickle.dumps(x, -1), 9)


def unprep(x):
    """
    Helper function to decompress and unpickle a log entry and return the
    associated Python object.
    """
    return pickle.loads(zlib.decompress(x))


def get_log_filename(db_name, path, logname):
    '''
    Helper function, returns the filename where a given log is stored on disk.

    **Parameters:**

    * `db_name`: the name of the database to look in
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    '''
    if path:
        course = path[0]
        return os.path.join(base_context.cs_data_root, '__LOGS__', '_courses', course, db_name, *(path[1:]), '%s.log' % logname)
    else:
        return os.path.join(base_context.cs_data_root, '__LOGS__', db_name, *path, '%s.log' % logname)


def update_log(db_name, path, logname, new, lock=True):
    """
    Adds a new entry to the end of the specified log.

    **Parameters:**

    * `db_name`: the name of the database to update
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    * `new`: the Python object that should be added to the end of the log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this update
    """
    fname = get_log_filename(db_name, path, logname)
    #get an exclusive lock on this file before making changes
    # look up the separator and the data
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        try:
            create_if_not_exists(os.path.dirname(fname))
            with open(fname, 'rb') as f:
                sep = f.readline().strip()
                data = f.read()
            if sep == '':
                raise Exception
        except:
            overwrite_log(db_name, path, logname, new, lock=False)
            return
        new = prep(new)
        if good_separator(sep, new):
            # if the separator is still okay, just add the new entry to the end
            # of the file
            with open(fname, 'ab') as f:
                f.write(new + sep)
        else:
            # if not, rewrite the whole file with a new separator
            entries = [i for i in data.split(sep) if i != b''] + [new]
            sep = get_separator(data, new)
            with open(fname, 'wb') as f:
                f.write(sep + b'\n')
                f.write(sep.join(entries) + sep)


def _overwrite_log(fname, new):
    create_if_not_exists(os.path.dirname(fname))
    new = prep(new)
    sep = get_separator(new)
    with open(fname, 'wb') as f:
        f.write(sep + b'\n')
        f.write(new + sep)


def overwrite_log(db_name, path, logname, new, lock=True):
    """
    Overwrites the entire log with a new log with a single (given) entry.

    **Parameters:**

    * `db_name`: the name of the database to overwrite
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log
    * `new`: the Python object that should be contained in the new log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this update
    """
    #get an exclusive lock on this file before making changes
    fname = get_log_filename(db_name, path, logname)
    cm = FileLock(fname) if lock else passthrough()
    with cm as l:
        _overwrite_log(fname, new)


def _read_log(db_name, path, logname, lock=True):
    fname = get_log_filename(db_name, path, logname)
    #get an exclusive lock on this file before reading it
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        try:
            f = open(fname, 'rb')
            sep = f.readline().strip()
            this = ''
            for i in f.read().split(sep):
                yield unprep(i)
            raise StopIteration
        except:
            raise StopIteration


def read_log(db_name, path, logname, lock=True):
    """
    Reads all entries of a log.

    **Parameters:**

    * `db_name`: the name of the database to read
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log

    **Optional Parameters:**

    * `lock` (default `True`): whether the database should be locked during
        this read

    **Returns:** a list containing the Python objects in the log
    """
    return list(_read_log(db_name, path, logname, lock))


def most_recent(db_name, path, logname, default=None, lock=True):
    '''
    Ignoring most of the log, grab the last entry.

    This code works by reading backward through the log until the separator is
    found, treating the piece of the file after the last separator as a log
    entry, and using `unprep` to return the associated Python object.

    Based on <a
    href="http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail"
    target="_blank">code by S.Lott and Pykler</a>

    **Parameters:**

    * `db_name`: the name of the database to read
    * `path`: the path to the page associated with the log
    * `logname`: the name of the log

    **Optional Parameters:**

    * `default` (default `None`): the value to be returned if the log contains
        no entries or does not exist
    * `lock` (default `True`): whether the database should be locked during
        this read

    **Returns:** a single Python object representing the most recent entry in
    the log.
    '''
    fname = get_log_filename(db_name, path, logname)
    if not os.path.isfile(fname):
        return default
    #get an exclusive lock on this file before reading it
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        f = open(fname, 'rb')
        sep = f.readline().strip()
        lsep = len(sep)
        offset = lsep + 1
        f.seek(0, 2)
        blocksize = 1024
        numbytes = f.tell() - offset
        block = -1
        data = b''
        while True:
            if numbytes - blocksize > offset:
                # if we are more than one "blocksize" from the start of
                # the file (counting from the end), add that block to our
                # buffer and continue on
                f.seek(block * blocksize, 2)
                data = f.read(blocksize) + data
            else:
                # otherwise, seek to the start of the file and read
                # through to the end
                f.seek(offset, 0)
                # need to split on this next line because some entries
                # may be shorter than one "blocksize"
                data = (f.read(numbytes) + data)[:-lsep].split(sep)[-1]
                f.close()
                return unprep(data)
            # update our counters
            block -= 1
            numbytes -= blocksize
            # if we found a break (or multiple breaks), we are done.  grab
            # the data and return.
            breaks = data[:-lsep].count(sep)
            if breaks >= 1:
                f.close()
                data = data[:-lsep]
                t = data[data.rfind(sep)+lsep:]
                return unprep(t)


def modify_most_recent(db_name, path, logname, default=None, transform_func=lambda x: x, method='update', lock=True):
    fname = get_log_filename(db_name, path, logname)
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        old_val = most_recent(db_name, path, logname, default, lock=False)
        new_val = transform_func(old_val)
        if method == 'update':
            updater = update_log
        else:
            updater = overwrite_log
        updater(db_name, path, logname, new_val, lock=False)
    return new_val
