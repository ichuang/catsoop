# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

# Checks for valid configuration

import os
import stat
import traceback

config_errors = []

try:
    from config import *
except Exception as e:
    config_errors.append('error in config.py: %s' % (e, ))

# check for valid fs_root
_fs_root_error = ('cs_fs_root must be a directory containing the '
                  'cat-soop source code')
if not os.path.isdir(cs_fs_root):
    config_errors.append(_fs_root_error)
else:
    root = os.path.join(cs_fs_root, 'catsoop')
    if not os.path.isdir(root):
        config_errors.append(_fs_root_error)
    else:
        contents = os.listdir(root)
        if not all(('%s.py' % i in contents or i in contents)
                   for i in cs_all_modules):
            config_errors.append(_fs_root_error)
# check for valid data_root
if not os.path.isdir(cs_data_root):
    config_errors.append('cs_data_root must be an existing directory')
else:
    if not os.access(cs_data_root, os.W_OK):
        config_errors.append('the web server must be able to write to '
                                 'cs_data_root')
