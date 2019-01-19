# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
import traceback
import importlib

from http.cookies import SimpleCookie

from . import cslog
from . import debug_log
from . import base_context

importlib.reload(base_context)

LOGGER = debug_log.LOGGER

_nodoc = {"SimpleCookie", "make_session_dir"}

VALID_SESSION_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
"""
Regular expression matching a valid session id name (32 hexadecimal characters)
"""

EXPIRE = 48 * 3600
"""
Number of seconds since last action to keep a session as valid.
Defaults to 48 hours.
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
    make_session_dir()
    now = time.time()
    for i in os.listdir(SESSION_DIR):
        fullname = os.path.join(SESSION_DIR, i)
        try:
            if os.stat(fullname).st_mtime < now - EXPIRE:
                os.unlink(fullname)
        except:
            pass
    if "HTTP_COOKIE" in environ:
        try:
            cookies = environ["HTTP_COOKIE"]
            cookies = cookies.replace(
                " ", ""
            )  # avoid unnecessary errors from cookie values with embedded spaces
            cookie_sid = SimpleCookie(cookies)["sid"].value
            if VALID_SESSION_RE.match(cookie_sid) is None:
                LOGGER.error(
                    "[session] cookie_sid (%s) session mismatch, generating new sid"
                    % cookie_sid
                )
                return new_session_id(), True
            return cookie_sid, False
        except Exception as err:
            LOGGER.error(
                "[session] Error encountered retrieving session ID, err=%s" % str(err)
            )
            LOGGER.error("[session] traceback=%s" % traceback.format_exc())
            LOGGER.error("[session] HTTP_COOKIE: %s" % environ["HTTP_COOKIE"])
            LOGGER.error(
                "[session] SimpleCookie: %s" % SimpleCookie(environ["HTTP_COOKIE"])
            )
            return new_session_id(), True
    else:
        return new_session_id(), True


def make_session_dir():
    """
    Create the session directory if it does not exist.
    """
    os.makedirs(SESSION_DIR, exist_ok=True)


def get_session_data(context, sid):
    """
    Returns the session data associated with a given session ID

    **Parameters:**

    * `context`: the context associated with this request
    * `sid`: the session ID to look up

    **Returns:** a dictionary mapping session variables to their values
    """
    make_session_dir()
    fname = os.path.join(SESSION_DIR, sid)
    with cslog.log_lock(["_sessions", sid]):
        try:
            with open(fname, "rb") as f:
                out = cslog.unprep(f.read())
        except:
            out = {}  # default to returning empty session
    return out


def set_session_data(context, sid, data):
    """
    Replaces a given session's data with the dictionary provided

    **Parameters:**

    * `context`: the context associated with this request
    * `sid`: the session ID to replace
    * `data`: a dictionary mapping session variables to values

    **Returns:** `None`
    """
    make_session_dir()
    fname = os.path.join(SESSION_DIR, sid)
    with cslog.log_lock(["_sessions", sid]):
        with open(fname, "wb") as f:
            f.write(cslog.prep(data))
