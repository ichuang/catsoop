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
Various utilies (primarily for user management)
"""

import os

from . import loader


def _hide(n):
    return n[0] in ("_", ".") or not n.endswith(".py")


def users_dir(context, course):
    """
    Determine the location of the given course's `__USERS__` directory on disk.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the name of the course, as a string

    **Returns:** a string containing the location of the given course's
    `__USERS__` directory.
    """
    root = context["cs_data_root"]
    return os.path.join(root, "courses", course, "__USERS__")


def list_all_users(context, course):
    """
    List all the users in a course

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the name of the course, as a string

    **Returns:** a list of the usernames of all users in the course
    """
    usrdir = users_dir(context, course)
    return [i.rsplit(".", 1)[0] for i in os.listdir(usrdir) if not _hide(i)]


def read_user_file(context, course, user, default=None):
    """
    Retrieve the contents of a given user's `__USERS__` file within a course.

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the name of the course, as a string
    * `user: the name of a user, as a string

    **Optional Parameters:**

    * `default` (default `None`): the value to be returned if the given user
        does not have a `__USERS__` file

    **Returns:** a dictionary containing the variables defined in the given
    user's file
    """
    user_file = os.path.join(users_dir(context, course), "%s.py" % user)
    if os.path.isfile(user_file):
        uinfo = {}
        with open(user_file) as f:
            exec(f.read(), uinfo)
        uinfo["username"] = user
        loader.clean_builtins(uinfo)
        return uinfo
    else:
        return default


def all_users_info(context, course, filter_func=lambda uinfo: True):
    """
    Return a mapping from usernames to user information

    **Parameters:**

    * `context`: the context associated with this request
    * `course`: the name of the course, as a string

    **Optional Parameters:**

    * `filter_func` (default `lambda uinfo: True`): a function mapping user
        information dictionaries to Booleans; a user is only included in the
        output if the function returns `True` when invoked on their user
        information dictionary

    **Returns:** a dictionary mapping usernames to user information
    dictionaries
    """
    all_users = {
        u: read_user_file(context, course, u, {})
        for u in list_all_users(context, course)
    }
    return {k: v for k, v in all_users.items() if filter_func(v)}
