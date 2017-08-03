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
Simple session handling.
"""

import os
import re
import time
import uuid
import importlib

import rethinkdb as r

from http.cookies import SimpleCookie

from . import cslog
from . import base_context
from .tools import filelock

importlib.reload(base_context)

EXPIRES = 60*60*24*2

def new_session_id():
    """
    Returns a new session ID

    @return: A string containing a new session ID
    """
    c = r.connect(db='catsoop')
    r.table('sessions').filter(r.row['time'] < time.time() - EXPIRES).delete(durability='soft').run(c)
    res = r.table('sessions').insert({'time': time.time(), 'data': {}}).run(c)
    out = res['generated_keys'][0]
    c.close()
    return out


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
            c = r.connect(db='catsoop')
            cookie_sid = SimpleCookie(environ['HTTP_COOKIE'])['sid'].value
            if len(list(r.table('sessions').filter(cookie_sid).run(c))) == 0:
                out = new_session_id(), True
            else:
                r.table('sessions').filter(cookie_sid).update({'time': time.time()}).run(c)
                out = cookie_sid, False
            c.close()
            return out
        except:
            return new_session_id(), True
    else:
        return new_session_id(), True


def get_session_data(context, sid):
    """
    Returns the session data associated with a given session ID

    @param sid: The session ID to look up
    @return: A dictionary mapping session variables to their values
    """
    c = r.connect(db='catsoop')
    out = list(r.table('sessions').filter(sid).run(c))
    if len(out) == 0:
        rtn = {}
    else:
        rtn = {k:v for k, v in out[0].get('data', {}).items() if k != 'id'}
    c.close()
    return rtn


def set_session_data(context, sid, data):
    """
    Replaces a given session's data with the dictionary provided

    @param sid: The session ID to replace
    @param data: A dictionary mapping session variables to values
    """
    c = r.connect(db='catsoop')
    r.table('sessions').filter(sid).update({'data': data}).run(c)
    c.close()
