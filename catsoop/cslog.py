# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
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
import ast
import zlib
import pickle
import contextlib

from collections import OrderedDict

from .tools.pretty import pretty

_nodoc = {'passthrough', 'FileLock', 'SEP_CHARS', 'create_if_not_exists',
          'get_separator', 'good_separator', 'modify_most_recent'}

@contextlib.contextmanager
def passthrough():
    yield

from . import base_context
from .tools.filelock import FileLock


def create_if_not_exists(directory):
    os.makedirs(directory, exist_ok=True)


def prep(x):
    """
    Helper function to pickle and compress a Python object.
    """
    return pretty(x)


def unprep(x):
    return literal_eval(x)


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


sep = '\n\n'

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
    assert can_log(new), "Can't log: %r" % new
    fname = get_log_filename(db_name, path, logname)
    #get an exclusive lock on this file before making changes
    # look up the separator and the data
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'a') as f:
            f.write(prep(new) + sep)


def _overwrite_log(fname, new):
    assert can_log(new), "Can't log: %r" % new
    create_if_not_exists(os.path.dirname(fname))
    with open(fname, 'w') as f:
        f.write(prep(new) + sep)


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
            f = open(fname, 'r')
            for i in f.read().split(sep):
                if i:
                    yield unprep(i)
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
        with open(fname, 'r') as f:
            return unprep(f.read().rsplit(sep, 2)[-2])


def modify_most_recent(db_name, path, logname, default=None, transform_func=lambda x: x, method='update', lock=True):
    fname = get_log_filename(db_name, path, logname)
    cm = FileLock(fname) if lock else passthrough()
    with cm as lock:
        old_val = most_recent(db_name, path, logname, default, lock=False)
        new_val = transform_func(old_val)
        assert can_log(new_val), "Can't log: %r" % new_val
        if method == 'update':
            updater = update_log
        else:
            updater = overwrite_log
        updater(db_name, path, logname, new_val, lock=False)
    return new_val

_unprep_funcs = {
    'OrderedDict': OrderedDict,
    'frozenset': frozenset,
    'set': set,
}

def unprep(node_or_string):
    """
    Helper function to read a log entry and return the associated Python
    object.  Forked from Python 3.5's ast.literal_eval function:

    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, bytes, numbers, tuples, lists, dicts,
    sets, booleans, and None.

    Modified for CAT-SOOP to include collections.OrderedDict.
    """
    if isinstance(node_or_string, str):
        node_or_string = ast.parse(node_or_string, mode='eval')
    if isinstance(node_or_string, ast.Expression):
        node_or_string = node_or_string.body
    def _convert(node):
        if isinstance(node, (ast.Str, ast.Bytes)):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Tuple):
            return tuple(map(_convert, node.elts))
        elif isinstance(node, ast.List):
            return list(map(_convert, node.elts))
        elif isinstance(node, ast.Set):
            return set(map(_convert, node.elts))
        elif isinstance(node, ast.Dict):
            return dict((_convert(k), _convert(v)) for k, v
                        in zip(node.keys, node.values))
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.UnaryOp) and \
             isinstance(node.op, (ast.UAdd, ast.USub)) and \
             isinstance(node.operand, (ast.Num, ast.UnaryOp, ast.BinOp)):
            operand = _convert(node.operand)
            if isinstance(node.op, ast.UAdd):
                return + operand
            else:
                return - operand
        elif isinstance(node, ast.BinOp) and \
             isinstance(node.op, (ast.Add, ast.Sub)) and \
             isinstance(node.right, (ast.Num, ast.UnaryOp, ast.BinOp)) and \
             isinstance(node.left, (ast.Num, ast.UnaryOp, ast.BinOp)):
            left = _convert(node.left)
            right = _convert(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            else:
                return left - right
        elif isinstance(node, ast.Call) and \
             isinstance(node.func, ast.Name) and \
             node.func.id in _unprep_funcs:
            return _unprep_funcs[node.func.id](*(_convert(i) for i in node.args))
        raise ValueError('malformed node or string: ' + repr(node))
    return _convert(node_or_string)


NoneType = type(None)
def can_log(x):
    """
    Checks whether a given value can be a log entry.
    """
    if isinstance(x, (str, bytes, int, float, complex, NoneType, bool)):
        return True
    elif isinstance(x, (list, tuple, set, frozenset)):
        return all(can_log(i) for i in x)
    elif isinstance(x, (dict, OrderedDict)):
        return all((can_log(k) and can_log(v)) for k,v in x.items())
    return False
