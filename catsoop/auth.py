# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

# User authentication

import os
import importlib

from . import loader
from . import base_context
importlib.reload(base_context)


def get_auth_type(context):
    """
    Returns a dictionary containing the variables defined in the
    authentication type specified by context['cs_auth_type'].
    """
    auth_type = context['cs_auth_type']
    fs_root = context.get('cs_fs_root', base_context.cs_fs_root)
    data_root = context.get('cs_data_root', base_context.cs_data_root)
    course = context['cs_course']

    tail = os.path.join('__AUTH__', auth_type, "%s.py" % auth_type)
    course_loc = os.path.join(data_root, 'courses', course, tail)
    global_loc = os.path.join(fs_root, tail)

    e = dict(context)
    # look in course, then global; error if not found
    if (course is not None and os.path.isfile(course_loc)):
        execfile(course_loc, e)
    elif os.path.isfile(global_loc):
        execfile(global_loc, e)
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

    If cs_auth_type is C{'login'}, then the user will log in via a form, and
    user information is pulled from logs on disk.  Information about the user
    currently logged in to the system is stored in the session.
    """
    form = context.get('cs_form', {})
    if 'ajax_username' in form:
        import sys
        uname = form['ajax_username']
        if form['ajax_secret'] != context['cs_ajax_secret'](uname):
            return {}
        else:
            return {'username': uname, 'name': uname, 'email': uname}

    return get_auth_type(context)['get_logged_in_user'](context)


def get_user_information(context):
    """
    Based on the context, load extra information about the user.

    This method is used to load any information specified about the user
    in a course's __USERS__ directory, or from a global log.  For example,
    course-level permissions are loaded this way.

    Returns a dictionary like that returned by get_logged_in_user, but
    (possibly) with additional mappings as specified in the loaded file.
    """
    start = context['cs_user_info']
    if context.get('cs_course', None) is not None:
        fname = os.path.join(context['cs_data_root'], 'courses',
                             context['cs_course'], '__USERS__',
                             "%s.py" % context['cs_username'])
    else:
        fname = os.path.join(context['cs_data_root'], '__LOGS__',
                             context['cs_username'])
    if os.path.exists(fname):
        text = open(fname).read()
        exec(text, start)

    # permissions handling
    if 'permissions' not in start:
        if 'role' not in start:
            start['role'] = context.get('cs_default_role', None)
        plist = context.get('cs_permissions', {})
        defaults = context.get('cs_default_permissions', [])
        start['permissions'] = plist.get(start['role'], defaults)

    loader.clean_builtins(start)

    # impersonation
    if ('as' in context['cs_form']) and ('real_user' not in start):
        if 'impersonate' not in start['permissions']:
            return start
        old = dict(start)
        old['p'] = start['permissions']
        context['cs_username'] = context['cs_form']['as']
        start['real_user'] = old
        start['username'] = start['name'] = context['cs_username']
        start['role'] = None
        start['permissions'] = []
        start = get_user_information(context)
    return start
