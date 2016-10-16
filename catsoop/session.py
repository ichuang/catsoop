# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.
"""
Simple session handling.
"""

import os
import re
import time
import uuid
import importlib

from http.cookies import SimpleCookie

from . import logging
from . import base_context
from .tools import filelock

importlib.reload(base_context)


VALID_SESSION_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
"""
Regular expression matching a valid session id name (32 hexadecimal characters)
"""

EXPIRE = 24 * 3600
"""
Number of seconds since last action to keep a session as valid.
Defaults to 24 hours
"""

SESSION_DIR = os.path.join(base_context.cs_data_root, "__SESSIONS__")
"""
The directory where sessions will be stored.
"""


def new_session_id():
    """
    Returns a new session ID

    @return: A string containing a new session ID
    """
    return uuid.uuid4().hex


def get_session_id(environ):
    """
    Returns the appropriate session id for this request

    @param environ: A dictionary mapping environment variables to their values
    @return: A tuple C{(sid, new)}, where C{sid} is a string containing the
    session ID, and C{new} is a boolean that takes value C{True} if
    the session ID is new (just now generated), and C{False} if the
    session ID is not new.
    """
    if 'HTTP_COOKIE' in environ:
        try:
            cookie_sid = SimpleCookie(environ['HTTP_COOKIE'])['sid'].value
            if VALID_SESSION_RE.match(cookie_sid) is None:
                return new_session_id(), True
            return cookie_sid, False
        except:
            return new_session_id(), True
    else:
        return new_session_id(), True


def make_session_dir():
    """
    Create the session directory if it does not exist.
    """
    if not os.path.isdir(SESSION_DIR):
        os.makedirs(SESSION_DIR)


def expire_sessions():
    """
    Expire sessions that have not been accessed within L{EXPIRE} seconds.
    """
    for fname in os.listdir(SESSION_DIR):
        fname = os.path.join(SESSION_DIR, fname)
        try:
            if os.stat(fname).st_atime < time.time() - EXPIRE:
                os.remove(fname)
        except:
            pass


def get_session_data(context, sid):
    """
    Returns the session data associated with a given session ID

    @param sid: The session ID to look up
    @return: A dictionary mapping session variables to their values
    """
    make_session_dir()
    fname = os.path.join(SESSION_DIR, sid)
    with filelock.FileLock(fname) as lock:
        try:
            with open(fname, 'rb') as f:
                out = logging.get_logger(context).unprep(f.read())
        except:
            out = {}  # default to returning empty session
    return out


def set_session_data(context, sid, data):
    """
    Replaces a given session's data with the dictionary provided

    @param sid: The session ID to replace
    @param data: A dictionary mapping session variables to values
    """
    make_session_dir()
    fname = os.path.join(SESSION_DIR, sid)
    with filelock.FileLock(fname) as lock:
        with open(fname, 'wb') as f:
            f.write(logging.get_logger(context).prep(data))
    expire_sessions()
