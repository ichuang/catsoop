# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE
"""
Initial Context

Many of the variables in this file are special variables that affect the way
the page is rendered (these special variables can be overwritten by early loads
or late loads at lower levels).
"""

cs_version = '9.0.0+develop'
"""
CAT-SOOP's version number
"""

cs_fs_root = '/home/cat-soop/cat-soop'
"""
The directory where CAT-SOOP is located (the location of index.py).
"""

cs_data_root = r'/home/cat-soop/data'
"""
The directory where CAT-SOOP's data files are located.
"""

cs_url_root = 'http://cat-soop.org/try'
"""
The URL root (without trailing slash).  Going to this URL should lead the user
to CAT-SOOP's information page.
"""

cs_auth_type = 'login'
"""
Which authentication type to use ('login' to use a form, 'cert' to read client
certificates).
"""


# Default Page Content
cs_title = 'CAT-SOOP'
"""
Special: The page title, to be displayed in the browser's title bar
"""

cs_base_logo_text = ('\            '
                   '\n/    /\__/\  '
                   '\n\__=(  o_O )='
                   '\n(__________) '
                   '\n |_ |_ |_ |_ ')
"""
Special: Text representing the CAT-SOOP Logo
"""

_hdr = '''<pre style="font-size: 50%%">%s</pre>CAT-SOOP'''
cs_header = _hdr % cs_base_logo_text
"""
Special: The main header, displayed at the top of the page
"""

cs_subheader = ''
"""
Special: Sub-header, displayed below the main header
"""

cs_footer = ''
"""
Special: Footer, displayed in addition to the "powered by CAT-SOOP" link
"""

cs_navigation = ''
"""
Special: Navigation menu
"""

cs_scripts = ''
"""
Special: HTML to import additional scripts; included in the page's <head> tags
"""

cs_side_menu = ''
"""
Special: Additional menu space
"""

cs_bottom_menu = ''
"""
Special: Additional menu space
"""

cs_content_header = ('<style>'
                     '.cs_bluebold {color: #00F; font-weight: bold}'
                     '</style>'
                     '<h1>'
                     '<span class="cs_bluebold">C</span>AT-SOOP is an '
                     '<span class="cs_bluebold">A</span>utomatic '
                     '<span class="cs_bluebold">T</span>utor for '
                     '<span class="cs_bluebold">S</span>ix-'
                     '<span class="cs_bluebold">O</span>h-'
                     '<span class="cs_bluebold">O</span>ne '
                     '<span class="cs_bluebold">P</span>roblems'
                     '</h1>')
"""
Special: The text to be displayed at the top of the "content" block.
"""

cs_content = ''
"""
Special: The content of the page
"""

cs_footnotes = ''
"""
Special: A string containing footenotes, if any
"""

cs_template = 'BASE/templates/main.template'
"""
Special: The template file to use to render the page
"""

# Default Look and Feel
cs_theme = 'BASE/themes/base.css'
"""
Special: A URL pointing to the page's CSS stylesheet
"""

cs_icon_url = 'BASE/images/favicon.gif'
"""
Special: A URL pointing to the page's favicon
"""

cs_course = None
"""
The course associated with a request
"""

try:
    https = cs_env.get('HTTPS', '0')
    scheme = cs_env.get('REQUEST_SCHEME', 'http').lower()
    if (https not in {'1', 'on'} and scheme != 'https' and
            cs_url_root.startswith('https')):
        cs_url_root = 'http' + cs_url_root[cs_url_root.find(':'):]
except:
    pass

# Debugging Function

cs_debug_log_location = '/tmp/catsoop.log'
"""
The filename where the user debug log should be stored (via cs_debug)
"""


def cs_debug(*values, tag=''):
    """
    Write values to cs_debug_log_location, with a timestamp and an optional tag.
    If cs_debug_log_location is None, do nothing.
    """
    if cs_debug_log_location is None:
        return
    from datetime import datetime
    with open(cs_debug_log_location, 'a') as myfile:
        print(datetime.now().time(), tag, *values, file=myfile)

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
