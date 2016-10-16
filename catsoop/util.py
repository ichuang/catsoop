# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import os

from . import loader

def _hide(n):
    return n[0] in ('_', '.') or not n.endswith('.py')


def users_dir(context, course):
    root = context['cs_data_root']
    return os.path.join(root, 'courses', course, '__USERS__')


def list_all_users(context, course):
    usrdir = users_dir(context, course)
    return [i.rsplit('.', 1)[0] for i in os.listdir(usrdir) if not _hide(i)]


def read_user_file(context, course, user, default=None):
    user_file = os.path.join(users_dir(context, course), "%s.py" % user)
    if os.path.isfile(user_file):
        uinfo = {}
        exec(open(user_file).read(), uinfo)
        uinfo['username'] = user
        loader.clean_builtins(uinfo)
        return uinfo
    else:
        return default
