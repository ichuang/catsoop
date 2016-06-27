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


def prep(x):
    """
    Prepare a Python object for insertion to a database.

    @param x: An arbitrary (serializable) Python object
    @return: An instance of C{sqlite3.Binary} representing the zipped, pickled
    object, ready for insertion into a database
    """
    return zlib.compress(pickle.dumps(x, -1), 9)


def unprep(x):
    """
    Reconstruct a Python object from the data stored in a database.

    @param x: An string representing a zipped, pickled Python object (of the
    form produced by L{prep})
    @return: The object represented by C{x}
    """
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

    @param directory: The directory to check/create
    '''
    if not os.path.isdir(directory):
        os.makedirs(directory)


def get_log_filename(course, db_name):
    '''
    Returns the filename where a given database is stored on disk.

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param db_name: The name of the database we want

    '''
    if course is not None:
        d = os.path.join(gb.cs_data_root, 'courses', course, '__LOGS__')
        create_if_not_exists(d)
        fname = os.path.join(d, db_name + '.db')
    else:
        d = os.path.join(gb.cs_data_root, '__LOGS__')
        create_if_not_exists(d)
        fname = os.path.join(gb.cs_data_root, '__LOGS__', db_name + '.db')
    if os.path.dirname(os.path.abspath(fname)) != os.path.abspath(d):
        raise Exception("Cannot access log at %s" % fname)
    return fname


def sqlite_access(fname):
    """
    Helper used to access a given SQLite database.
    Initializes database if appropriate.

    @param fname: The filename at which the given log is stored
    @return: A tuple containing an C{sqlite} connection object and an C{sqlite}
    cursor object for the appropriate database
    """
    c = sqlite3.connect(fname)
    c.text_factory = str
    c.execute(MAKETABLE)
    c.commit()
    return c, c.cursor()


def update_log(course, db_name, logname, new):
    """
    Adds a new entry to the specified log.

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param db_name: The name of the database we are accessing
    @param logname: The name of the specific log we want to update
    @param new: A Python object representing the new log entry
    """
    conn, c = sqlite_access(get_log_filename(course, db_name))
    c.execute(UPDATE, (logname, sqlite3.Binary(prep(new), )))
    conn.commit()
    conn.close()


def overwrite_log(course, db_name, logname, new):
    """
    Overwrites the most recent entry in the specified log.

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param db_name: The name of the database we are accessing
    @param logname: The name of the specific log we want to update
    @param new: A Python object representing the new log entry
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

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param db_name: The name of the database we are accessing
    @param logname: The name of the specific log we want to update
    @return: A list containing all the log entries (unpickled to create
    equivalent Python objects), in the order they were added to the log.
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

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param db_name: The name of the database we are accessing
    @param logname: The name of the specific log we want to update
    @param default: The value to return if no entries exist in the log
    (defaults to C{None})
    @return: A Python object representing the most recent entry made to this
    log, or L{default} if no such entry exists
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
