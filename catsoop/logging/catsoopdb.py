# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE
"""
Logging mechanisms in catsoopdb
"""

import gb
import os.path
from filelock import FileLock
import zlib
import re
import cstime

SEPARATOR = '\nTHISISASEPARATOR(o_O)\n'
RESEPARATOR = r'\nTHISISASEPARATOR\(o_O\)\n'

def get_log_filename(course,log_name):
    '''
    Returns the filename where a given log is stored on disk.

    @param course: A string containing the name of the course (a subdirectory
    in C{courses}), or C{None} to access a global log
    @param log_name: A string containing the name of the log to be accessed

    '''
    if course is not None:
        return os.path.join(gb.catsoop_data_root,'courses',course,'__LOGS__',log_name)
    else:
        return os.path.join(gb.catsoop_data_root,'__LOGS__',log_name)

def generic_change_log(course, log_name, new, mode):
    fname = get_log_filename(course,log_name)
    #get an exclusive lock on this file before making changes
    with FileLock(fname) as lock:
        #write representation to file
        f = open(fname,mode)
        f.write(zlib.compress(repr(new),9) + SEPARATOR)
        f.close()
        return True

def update_log(course, log_name, new):
    return generic_change_log(course, log_name, new, 'a')

def overwrite_log(course, log_name, new):
    return generic_change_log(course, log_name, new, 'w')

def read_log(course,log_name):
    '''
    Read the data from a log.  This is an iterator.
    '''
    fname = get_log_filename(course,log_name)
    #get an exclusive lock on this file before reading it
    with FileLock(fname) as lock:
        try:
            f = open(fname,'r')
            out = []
            this = ''
            for line in f:
                if line == SEPARATOR.lstrip():
                    yield eval(zlib.decompress(this))
                    this = ''
                else:
                    this += line
            f.close()
            raise StopIteration
        except:
            raise StopIteration

def most_recent(course,log_name,default=None):
    '''
    Ignoring most of the log, grab the last entry

    Based on code by S.Lott and Pykler at:
    U{http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail}
    '''
    fname = get_log_filename(course,log_name)
    #get an exclusive lock on this file before reading it
    with FileLock(fname) as lock:
        try:
            f = open(fname,'r')
            f.seek(0,2)
            buffersize = 1024
            numbytes = f.tell()
            block = -1
            data = ''
            while True:
                if numbytes - buffersize > 0:
                    f.seek(block*buffersize, 2)
                    data = f.read(buffersize) + data
                else:
                    f.seek(0,0)
                    data = (f.read(numbytes) + data)[:-len(SEPARATOR)]
                    f.close()
                    if SEPARATOR in data: #new stupid special case
                        data = data[list(re.finditer(RESEPARATOR,data))[-1].start()+len(SEPARATOR):]
                    return eval(zlib.decompress(data))
                block -= 1
                numbytes -= buffersize
                breaks = data[:-len(SEPARATOR)].count(SEPARATOR)
                if breaks == 1:
                    f.close()
                    t = data[data.find(SEPARATOR)+len(SEPARATOR):-len(SEPARATOR)]
                    return eval(zlib.decompress(t))
        except:
            return default

def read_file_update_log(course, log_name, filename):
    """
    return the contents of the specified file, after first checking
    whether the file has been changed.

    used for user information, and for activity files
    """
    with FileLock(filename) as lock: #maybe this lock isn't necessary?
        last = most_recent(course,log_name)
        current = open(filename).read()
        if last is None: #this is a new log entry
             changed = True
        else:
            _, old = last
            changed = old != current
        if changed:
            timestamp = cstime.detailed_timestamp(cstime.now())
            update_log(course,log_name,(timestamp,current))
    return current
