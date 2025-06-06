# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
Simple session handling using the `cslog` package.
"""

import os
import re
import time
import uuid
import hashlib
import traceback
import importlib

from . import util
from . import cslog
from . import base_context

importlib.reload(base_context)

_nodoc = {"make_session_dir"}

VALID_SESSION_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
"""
Regular expression matching a valid session id name (32 hexadecimal characters)
"""

EXPIRE = 14 * 24 * 60 * 60
"""
Number of seconds since last action to keep a session as valid.
Defaults to two weeks.
"""

SESSION_DIR = os.path.join(base_context.cs_data_root, "_sessions")
"""
The directory where sessions will be stored.
"""


def new_session_id():
    """
    Returns a new session ID

    **Returns:** a string containing a new session ID
    """
    return uuid.uuid4().hex


def get_session_id(environ):
    """
    Returns the appropriate session id for this request, generating a new one
    if necessary.

    As a side-effect, deletes all expired sessions.

    **Parameters:**

    * `environ`: a dictionary mapping environment variables to their values

    **Returns:** a tuple `(sid, new)`, where `sid` is a string containing the
    session ID, and `new` is a Boolean that takes value `True` if the session
    ID is new (just now generated), and `False` if the session ID is not new.
    """
    # clear out dead sessions first
    cslog.clear_old_logs("_sessions", [], EXPIRE)

    COOKIE_REGEX = re.compile(
        r"(?:^|;)\s*catsoop_sid_%s\s*=\s*([^;\s]*)\s*(?:;|$)" % util.catsoop_loc_hash()
    )
    try:
        cookie_sid = COOKIE_REGEX.search(environ["HTTP_COOKIE"]).group(1)
        if VALID_SESSION_RE.match(cookie_sid) is None:
            return new_session_id(), True
        return cookie_sid, False
    except Exception as err:
        return new_session_id(), True


def get_session_data(context, sid):
    """
    Returns the session data associated with a given session ID

    **Parameters:**

    * `context`: the context associated with this request
    * `sid`: the session ID to look up

    **Returns:** a dictionary mapping session variables to their values
    """
    return cslog.most_recent("_sessions", [], sid, {})


def set_session_data(context, sid, data):
    """
    Replaces a given session's data with the dictionary provided

    **Parameters:**

    * `context`: the context associated with this request
    * `sid`: the session ID to replace
    * `data`: a dictionary mapping session variables to values

    **Returns:** `None`
    """
    cslog.overwrite_log("_sessions", [], sid, data)
