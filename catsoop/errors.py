# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import traceback

from . import loader
from . import dispatch
from . import base_context

def html_format(string):
    """
    Returns an HTML-escaped version of the input string, suitable for
    insertion into a <pre> tag
    """
    for x, y in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('\t', '    '),
                 (' ', '&nbsp;')):
        string = string.replace(x, y)
    return string


def clear_info(context, text):
    """
    Clear sensitive information from a string
    """
    text = text.replace(
        context.get('cs_fs_root', base_context.cs_fs_root), '<CATSOOP ROOT>')
    text = text.replace(
        context.get('cs_data_root', base_context.cs_data_root), '<DATA ROOT>')
    for i, j in context.get('cs_extra_clear', []):
        text = text.replace(i, j)
    return text


def error_message_content(context):
    """
    Returns an HTML-ready string containing an error message.
    """
    return html_format(clear_info(context, traceback.format_exc()))


def do_error_message(context, msg=None):
    """
    Display an error message
    """
    new = dict(context)
    loader.load_global_data(new)
    new['cs_home_link'] = 'BASE'
    if 'cs_user_info' not in new:
        new['cs_user_info'] = {}
        new['cs_username'] = None
    if 'cs_handler' in new:
        del new['cs_handler']
    m = msg if msg is not None else error_message_content(context)
    new['cs_original_path'] = ''
    new['cs_content'] = ('<pre>ERROR:\n'
                         '%s</pre>') % ( m)
    e = ': <font color="red">ERROR</font>'
    new['cs_header'] = new.get('cs_header', '') + e
    new['cs_content_header'] = 'An Error Occurred:'
    new['cs_source_qstring'] = ''
    s, h, o = dispatch.display_page(new)
    o = o.replace(new['cs_base_logo_text'], error_500_logo)
    return ('500', 'Internal Server Error'), h, o


def do_404_message(context):
    """
    Display an error message
    """
    new = dict(context)
    loader.load_global_data(new)
    new['cs_home_link'] = 'BASE'
    if 'cs_user_info' not in new:
        new['cs_user_info'] = {}
        new['cs_username'] = None
    if 'cs_handler' in new:
        del new['cs_handler']
    new['cs_content'] = ('<pre>CAT-SOOP could not find the specified file or resource:\n'
                         '%r</pre>') % (new['cs_original_path'])
    new['cs_original_path'] = ''
    e = ': <font color="red">404</font>'
    new['cs_header'] = new.get('cs_header', '') + e
    new['cs_content_header'] = 'File/Resource Not Found'
    new['cs_source_qstring'] = ''
    s, h, o = dispatch.display_page(new)
    o = o.replace(new['cs_base_logo_text'], error_404_logo)
    return ('404', 'File Not Found'), h, o

error_404_logo = ("\   ???????? "
                "\n/    /\__/\  "
                "\n\__=(  @_@ )="
                "\n(__________) "
                "\n |_ |_ |_ |_ ")

error_500_logo = ("  _  _  _  _  "
                "\n  _|__|__|__| "
                "\n (  _     ___)"
                "\n=( x X  )=   \\"
                "\n  \/  \/     /"
                "\n             \\")
