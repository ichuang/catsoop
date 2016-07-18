# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.

# User authentication

import os
import importlib

from . import api
from . import loader
from . import logging
from . import base_context
importlib.reload(base_context)


def _execfile(*args):
    fn = args[0]
    with open(fn) as f:
        c = compile(f.read(), fn, 'exec')
    exec(c, *args[1:])


def get_auth_type(context):
    """
    Returns a dictionary containing the variables defined in the
    authentication type specified by context['cs_auth_type'].
    """
    auth_type = context['cs_auth_type']
    return get_auth_type_by_name(context, auth_type)


def get_auth_type_by_name(context, auth_type):
    fs_root = context.get('cs_fs_root', base_context.cs_fs_root)
    data_root = context.get('cs_data_root', base_context.cs_data_root)
    course = context['cs_course']

    tail = os.path.join('__AUTH__', auth_type, "%s.py" % auth_type)
    course_loc = os.path.join(data_root, 'courses', course, tail)
    global_loc = os.path.join(fs_root, tail)

    e = dict(context)
    # look in course, then global; error if not found
    if (course is not None and os.path.isfile(course_loc)):
        _execfile(course_loc, e)
    elif os.path.isfile(global_loc):
        _execfile(global_loc, e)
    else:
        # no valid auth type found
        raise Exception("Invalid cs_auth_type: %s" % auth_type)

    return e


def get_logged_in_user(context):
    """
    From the context, get information about the logged in user.

    If the context has an API token in it, that value will be used to determine
    who is logged in.

    If cs_auth_type is 'cert', then the information is pulled from the user's
    certificate (by way of environment variables).

    If cs_auth_type is 'login', then the user will log in via a form, and user
    information is pulled from logs on disk.  Information about the user
    currently logged in to the system is stored in the session.
    """
    # if an API token was specified, use the associated information and move on
    # this has the side-effect of renewing that token (moving back the
    # expiration time)
    api_user = api.get_logged_in_user(context)
    if api_user is not None:
        return api_user

    regular_user = get_auth_type(context)['get_logged_in_user'](context)
    if 'username' in regular_user:
        # successful login.  check for existing token
        cslog = logging.get_logger(context)
        tok = cslog.most_recent(None, regular_user['username'],
                                  'api_token', None)
        if tok is None:
            # if no token found, create a new one.
            tok = api.initialize_api_token(context, regular_user)
        regular_user['api_token'] = tok
    return regular_user



def get_user_information(context):
    return _get_user_information(context, context['cs_user_info'],
                                 context.get('cs_course', None),
                                 context['cs_username'])


def _get_user_information(context, into, course, username, do_preload=False):
    """
    Based on the context, load extra information about the user.

    This method is used to load any information specified about the user
    in a course's __USERS__ directory, or from a global log.  For example,
    course-level permissions are loaded this way.

    Returns a dictionary like that returned by get_logged_in_user, but
    (possibly) with additional mappings as specified in the loaded file.
    """
    if course is not None:
        if do_preload:
            loader.load_global_data(context)
            loader.do_early_load(context, course, [], context)
        fname = os.path.join(context['cs_data_root'], 'courses',
                             context['cs_course'], '__USERS__',
                             "%s.py" % username)
    else:
        fname = os.path.join(context['cs_data_root'], '__LOGS__',
                             username)
    if os.path.exists(fname):
        text = open(fname).read()
        exec(text, into)

    # permissions handling
    if 'permissions' not in into:
        if 'role' not in into:
            into['role'] = context.get('cs_default_role', None)
        plist = context.get('cs_permissions', {})
        defaults = context.get('cs_default_permissions', ['view'])
        into['permissions'] = plist.get(into['role'], defaults)

    loader.clean_builtins(into)

    # impersonation
    if ('as' in context['cs_form']) and ('real_user' not in into):
        if 'impersonate' not in into['permissions']:
            return into
        old = dict(into)
        old['p'] = into['permissions']
        context['cs_username'] = context['cs_form']['as']
        into['real_user'] = old
        into['username'] = into['name'] = context['cs_username']
        into['role'] = None
        into['permissions'] = []
        into = get_user_information(context)
    return into
