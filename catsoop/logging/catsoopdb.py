# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE
"""
Logging mechanisms in catsoopdb
"""

import os
import re
import zlib
import pickle
import random
import string

from ..tools.filelock import FileLock

SEP_CHARS = (string.ascii_letters + string.digits).encode()


def good_separator(sep, data, new=None):
    return sep not in data and (new is None or sep not in new)


def get_separator(data, new=None):
    out = None
    while out is None or not good_separator(out, data, new=new):
        out = sum((random.choice(SEP_CHARS) for i in range(20)))
    return out


def create_if_not_exists(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)


def prep(x):
    return zlib.compress(pickle.dumps(x, -1), 9)


def unprep(x):
    return pickle.loads(zlib.decompress(x))


def get_log_filename(course, db_name, log_name):
    '''
    Returns the filename where a given log is stored on disk.
    '''
    base = os.path.join('__LOGS__', db_name, *(log_name.split('.')))
    if course is not None:
        return os.path.join(gb.catsoop_data_root, 'courses', course, base)
    else:
        return os.path.join(gb.catsoop_data_root, base)


def update_log(course, db_name, log_name, new):
    """
    Adds a new entry to the specified log.
    """
    fname = get_log_filename(course, db_name, log_name)
    #get an exclusive lock on this file before making changes
    # look up the separator and the data
    with FileLock(fname) as lock:
        try:
            create_if_not_exists(os.path.dirname(fname))
            with open(fname, 'rb') as f:
                sep = f.readline().strip()
                data = f.read()
            if sep == '':
                raise Exception
        except:
            overwrite_log(course, db_name, log_name, new)
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


def overwrite_log(course, db_name, log_name, new):
    """
    Overwrites the most recent entry in the specified log.
    """
    fname = get_log_filename(course, db_name, log_name)
    #get an exclusive lock on this file before making changes
    with FileLock(fname) as lock:
        create_if_not_exists(os.path.dirname(fname))
        sep = get_separator(new)
        with open(fname, 'wb') as f:
            f.write(sep + b'\n')
            f.write(new + sep)


def _read_log(course, db_name, log_name):
    fname = get_log_filename(course, db_name, log_name)
    #get an exclusive lock on this file before reading it
    with FileLock(fname) as lock:
        try:
            f = open(fname, 'rb')
            sep = f.readline().strip()
            this = ''
            for i in f.read().split(sep):
                yield unprep(i)
            raise StopIteration
        except:
            raise StopIteration


def read_log(course, db_name, log_name):
    """
    Reads all entries of a log.
    """
    return list(_read_log(course, db_name, log_name))


def most_recent(course, db_name, log_name, default=None):
    '''
    Ignoring most of the log, grab the last entry

    Based on code by S.Lott and Pykler at:
    http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
    '''
    fname = get_log_filename(course, db_name, log_name)
    #get an exclusive lock on this file before reading it
    with FileLock(fname) as lock:
        try:
            f = open(fname, 'rb')
            sep = f.readline().strip()
            f.seek(0, 2)
            blocksize = 1024
            numbytes = f.tell()
            block = -1
            data = b''
            lsep = len(sep)
            offset = lsep + 1
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
                    t = data[:-lsep][data.rfind(sep)+lsep:]
                    return unprep(t)
        except:
            return default
