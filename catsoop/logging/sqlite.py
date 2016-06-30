# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE
"""
Logging mechanisms in SQLite
"""

import os
import zlib
import pickle
import sqlite3
import importlib

from .. import base_context


def prep(x):
    return zlib.compress(pickle.dumps(x, -1), 9)


def unprep(x):
    return pickle.loads(zlib.decompress(x))


MAKETABLE = ('CREATE TABLE IF NOT EXISTS '
             'log (ix INTEGER PRIMARY KEY, '
             'logname TEXT NOT NULL, '
             'data BLOB NOT NULL)')
"""
SQLite query to initialize logging table
"""

UPDATE = 'INSERT INTO log VALUES(NULL,?,?)'
"""
SQLite query to add a new entry to a log
"""

OVERWRITE = ('INSERT OR REPLACE INTO log (ix,logname,data) '
             'VALUES((SELECT max(ix) FROM log WHERE logname=?), ?, ?)')
"""
SQLite query to update the most recent entry to a log
"""

READ = 'SELECT * FROM log WHERE logname=? ORDER BY ix ASC'
"""
SQLite query to grab all entries from a log
"""

MOSTRECENT = 'SELECT * FROM log WHERE logname=? ORDER BY ix DESC LIMIT 1'
"""
SQLite query to grab most recent entry from a log
"""


def create_if_not_exists(directory):
    '''
    Helper; creates a directory if it does not already exist.
    '''
    if not os.path.isdir(directory):
        os.makedirs(directory)


def get_log_filename(course, db_name):
    '''
    Returns the filename where a given database is stored on disk.
    '''
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


def update_log(course, db_name, logname, new):
    """
    Adds a new entry to the specified log.
    """
    conn, c = sqlite_access(get_log_filename(course, db_name))
    c.execute(UPDATE, (logname, sqlite3.Binary(prep(new), )))
    conn.commit()
    conn.close()


def overwrite_log(course, db_name, logname, new):
    """
    Overwrites the most recent entry in the specified log.
    """
    conn, c = sqlite_access(get_log_filename(course, db_name))
    c.execute(OVERWRITE, (logname,
                          logname,
                          sqlite3.Binary(prep(new)), ))
    conn.commit()
    conn.close()


def read_log(course, db_name, logname):
    """
    Reads all entries of a log.
    """
    try:
        fname = get_log_filename(course, db_name)
    except:
        return []
    if not os.path.isfile(fname):
        return []
    conn, c = sqlite_access(fname)
    c.execute(READ, (logname, ))
    out = [unprep(i[2]) for i in c.fetchall()]
    conn.close()
    return out


def most_recent(course, db_name, logname, default=None):
    """
    Reads the most recent entry from a log.
    """
    try:
        fname = get_log_filename(course, db_name)
    except:
        return default
    if not os.path.isfile(fname):
        return default
    conn, c = sqlite_access(fname)
    c.execute(MOSTRECENT, (logname, ))
    out = c.fetchone()
    conn.close()
    return unprep(out[2]) if out is not None else default
