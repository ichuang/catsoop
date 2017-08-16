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
Logging mechanisms in SQLite
"""

import os
import json
import sqlite3

from . import base_context as base_context
from .tools.filelock import FileLock

MAKETABLE = ('CREATE TABLE IF NOT EXISTS '
             'log (ix INTEGER PRIMARY KEY AUTOINCREMENT, '
             'path TEXT NOT NULL, '
             'logname TEXT NOT NULL, '
             'data TEXT NOT NULL)')
"""
SQLite query to initialize logging table
"""

UPDATE = 'INSERT INTO log VALUES(NULL,?,?,?)'
"""
SQLite query to add a new entry to a log
"""

OVERWRITE = ('INSERT OR REPLACE INTO log (ix,path,logname,data) '
             'VALUES((SELECT max(ix) FROM log WHERE path=? AND logname=?), ?, ?, ?)')
"""
SQLite query to update the most recent entry to a log
"""

READ = 'SELECT * FROM log WHERE path=? AND logname=? ORDER BY ix ASC'
"""
SQLite query to grab all entries from a log
"""

MOSTRECENT = 'SELECT * FROM log WHERE path=? AND logname=? ORDER BY ix DESC LIMIT 1'
"""
SQLite query to grab most recent entry from a log
"""


def create_if_not_exists(directory):
    '''
    Helper; creates a directory if it does not already exist.
    '''
    os.makedirs(directory, exist_ok=True)


def get_log_filename(path, db_name):
    '''
    Returns the filename where a given database is stored on disk.
    '''
    try:
        course = path[0]
    except:
        course = None
    if course is not None:
        d = os.path.join(base_context.cs_data_root, 'courses', course, '__LOGS__')
        create_if_not_exists(d)
        fname = os.path.join(d, db_name + '.db')
    else:
        d = os.path.join(base_context.cs_data_root, '__LOGS__')
        create_if_not_exists(d)
        fname = os.path.join(base_context.cs_data_root, '__LOGS__', db_name + '.db')
    if os.path.dirname(os.path.abspath(fname)) != os.path.abspath(d):
        raise Exception("Cannot access log at %s" % fname)
    return fname


def sqlite_access(fname):
    """
    Helper used to access a given SQLite database.
    Initializes database if appropriate.
    """
    c = sqlite3.connect(fname)
    c.text_factory = str
    c.execute(MAKETABLE)
    c.commit()
    return c, c.cursor()


def update_log(db_name, path, logname, new):
    """
    Adds a new entry to the specified log.
    """
    conn, c = sqlite_access(get_log_filename(path, db_name))
    c.execute(UPDATE, (json.dumps(path), logname, json.dumps(new)))
    conn.commit()
    conn.close()


def overwrite_log(db_name, path, logname, new):
    """
    Overwrites the most recent entry in the specified log.
    """
    conn, c = sqlite_access(get_log_filename(path, db_name))
    path = json.dumps(path)
    c.execute(OVERWRITE, (path,
                          logname,
                          path,
                          logname,
                          json.dumps(new), ))
    conn.commit()
    conn.close()


def read_log(db_name, path, logname):
    """
    Reads all entries of a log.
    """
    try:
        fname = get_log_filename(path, db_name)
    except:
        return []
    if not os.path.isfile(fname):
        return []
    conn, c = sqlite_access(fname)
    c.execute(READ, (json.dumps(path), logname, ))
    out = [json.loads(i[-1]) for i in c.fetchall()]
    conn.close()
    return out


def most_recent(db_name, path, logname, default=None):
    """
    Reads the most recent entry from a log.
    """
    try:
        fname = get_log_filename(path, db_name)
    except:
        return default
    if not os.path.isfile(fname):
        return default
    conn, c = sqlite_access(fname)
    c.execute(MOSTRECENT, (json.dumps(path), logname, ))
    out = c.fetchone()
    conn.close()
    return json.loads(out[-1]) if out is not None else default


def modify_most_recent(db_name, path, log, default=None, transform_func=lambda x: x, method='update'):
    fname = get_log_filename(path, db_name)
    with FileLock(fname) as lock:
        old_val = most_recent(db_name, path, log, default)
        new_val = transform_func(old_val)
        if method == 'update':
            updater = update_log
        else:
            updater = overwrite_log
        updater(db_name, path, log, new_val)
    return new_val
