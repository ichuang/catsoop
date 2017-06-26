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
Initial Context

Many of the variables in this file are special variables that affect the way
the page is rendered (these special variables can be overwritten by early loads
or late loads at lower levels).
"""

cs_version = '10.0.0+development'
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

cs_log_type = 'catsoopdb'
"""
Which backend to use for storing logs ('catsoopdb' and 'sqlite' are supported)
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

cs_main_page_text = ""
"""
Special: Text to be added to the main page
"""

cs_base_color = "#0000CC"
"""
Special: The base color to use to customize the main theme.
"""

cs_process_theme = True
"""
Special: Whether the theme should be "processed" by, e.g., evaluating Python code
"""

cs_welcome_message = ""
"""
Special: Welcome message displayed next to title in base theme.
"""

cs_header = "CAT-SOOP"
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

cs_top_menu = ''
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

cs_content_header = ('<span class="cs_base_bold">C</span>AT-SOOP is an '
                     '<span class="cs_base_bold">A</span>utomatic '
                     '<span class="cs_base_bold">T</span>utor for '
                     '<span class="cs_base_bold">S</span>ix-'
                     '<span class="cs_base_bold">O</span>h-'
                     '<span class="cs_base_bold">O</span>ne '
                     '<span class="cs_base_bold">P</span>roblems')
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


import os
import stat
import traceback

from datetime import datetime

_cs_config_errors = []

# try to import configuration from config.py

try:
    from .config import *
except Exception as e:
    _cs_config_errors.append('error in config.py: %s' % (e, ))

# Import all CAT-SOOP modules/subpackages

cs_all_pieces = [
    'api', 'auth', 'base_context', 'dispatch', 'errors', 'groups', 'language',
    'loader', 'logging', 'mail', 'session', 'time', 'tools', 'tutor', 'util'
]

cs_all_tools = ['data_uri', 'filelock', 'ply', 'markdown', 'bs4']

for i in cs_all_pieces:
    if i != 'base_context':
        exec('from . import %s' % i)
        exec('csm_%s = %s' % (i, i))

for i in cs_all_tools:
    exec('from .tools import %s' % i)
    exec('csm_tools.%s = %s' % (i, i))

# Checks for valid Configuration

# check for valid fs_root
_fs_root_error = ('cs_fs_root must be a directory containing the '
                  'cat-soop source code')
if not os.path.isdir(cs_fs_root):
    _cs_config_errors.append(_fs_root_error)
else:
    root = os.path.join(cs_fs_root, 'catsoop')
    if not os.path.isdir(root):
        _cs_config_errors.append(_fs_root_error)
    else:
        contents = os.listdir(root)
        if not all(('%s.py' % i in contents or i in contents)
                   for i in cs_all_pieces):
            _cs_config_errors.append(_fs_root_error)
# check for valid data_root
if not os.path.isdir(cs_data_root):
    _cs_config_errors.append('cs_data_root must be an existing directory')
else:
    if not os.access(cs_data_root, os.W_OK):
        _cs_config_errors.append('the web server must be able to write to '
                                 'cs_data_root')
