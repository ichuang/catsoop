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
Utilities for generating error messages and displaying error pages
"""

import os
import ast
import sys
import traceback

from . import loader
from . import dispatch
from . import base_context


def html_format(string):
    """
    Returns an HTML-escaped version of the input string, suitable for
    insertion into a &lt;pre&gt; tag

    **Parameters:**

    * `string`: the string to be escaped

    **Returns:** an HTML-escaped version of the input string
    """
    for x, y in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('\t', '    '),
                 (' ', '&nbsp;')):
        string = string.replace(x, y)
    return string


def clear_info(context, text):
    """
    Clear sensitive information from a string

    In particular, this function clears the `cs_fs_root` and `cs_data_root`
    from tracebacks, as well as any information specified by the
    `cs_extra_clear` variable.  It also removes the current user's session ID
    and API token if they are present.

    **Parameters:**

    * `context`: the context associated with this request
    * `text`: the text (typically a traceback) from which the information
        should be removed.

    **Returns:** the input string, but with sensitive data replaced.
    """
    text = text.replace(
        context.get('cs_fs_root', base_context.cs_fs_root), '<CATSOOP ROOT>')
    text = text.replace(
        context.get('cs_data_root', base_context.cs_data_root), '<DATA ROOT>')
    if 'cs_sid' in context:
        text = text.replace(context['cs_sid'], '<SESSION ID>')
    apitok = context.get('user_info', {}).get('api_token', None)
    if apitok is not None:
        text = text.replace(apitok, '<API TOKEN>')
    for i, j in context.get('cs_extra_clear', []):
        text = text.replace(i, j)
    return text


def error_message_content(context, html=True):
    """
    Returns a string containing an appropriate error message.

    This function bases its output on the last exception, but it also tries
    to take into account changes that the CAT-SOOP system makes to some input
    files.

    **Parameters:**

    * `context`: the context associated with this request

    **Optional Parameters:**

    * `html` (default `True`): whether the output should be HTML-escaped

    **Returns:** an error message appropriate for the last exception
    """
    data_cache = os.path.join(context['cs_data_root'], '_cached')
    e = sys.exc_info()
    tb_entries = traceback.extract_tb(e[2])
    new_entries = []
    for tb in tb_entries:
        fname, lineno, func, text = tb
        lo_fname = fname + '.line_offset'
        line_offset = 0
        if os.path.isfile(lo_fname):
            with open(lo_fname) as offsetfile:
                line_offset = ast.literal_eval(offsetfile.read())
        lineno -= line_offset
        if fname.startswith(data_cache):
            fname = fname[len(data_cache):]
        new_entries.append((fname, lineno, func, text))
    tb_text = ''.join(traceback.format_list(new_entries) +
                      traceback.format_exception_only(e[0], e[1]))
    i = clear_info(context, tb_text)
    if html:
        return html_format(i)
    return i


def do_error_message(context, msg=None):
    """
    Display an error page (500 Internal Server Error), including a sensible
    error message.

    **Parameters:**

    * `context`: the context associated with this request

    **Optional Parameters:**

    * `msg` (default `None`): a custom message to be displayed.  If no message
        is specified, the output from `catsoop.errors.error_message_content` is
        used (which tries to provide a meaningful error message based on the
        last exception.

    **Returns:** a 3-tuple, as expected by `catsoop.wsgi.application`
    """
    plain = 'data' in context.get('cs_form', {})
    new = dict(context)
    loader.load_global_data(new)
    new['cs_home_link'] = 'BASE'
    if 'cs_user_info' not in new:
        new['cs_user_info'] = {}
        new['cs_username'] = None
    if 'cs_handler' in new:
        del new['cs_handler']
    m = msg if msg is not None else error_message_content(
        context, html=(not plain))
    if plain:
        return ((500, 'Internal Server Error'), {
            'Content-type': 'text/plain',
            'Content-length': len(m.encode())
        }, m)
    new['cs_original_path'] = ''
    new['cs_content'] = ('<pre>ERROR:\n' '%s</pre>') % (m)
    e = ': <font color="red">ERROR</font>'
    new['cs_header'] = new.get('cs_header', '') + e
    new['cs_content_header'] = 'An Error Occurred:'
    new['cs_source_qstring'] = ''
    new['cs_source_qstring'] = ''
    new['cs_top_menu_html'] = ''
    new['cs_breadcrumbs_html'] = ''
    s, h, o = dispatch.display_page(new)
    o = o.replace(new['cs_base_logo_text'], error_500_logo)
    return ('500', 'Internal Server Error'), h, o


def do_404_message(context):
    """
    Display an error page (404 File Not Found), including a sensible error
    message.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** a 3-tuple, as expected by `catsoop.wsgi.application`
    """
    new = dict(context)
    loader.load_global_data(new)
    new['cs_home_link'] = 'BASE'
    if 'cs_user_info' not in new:
        new['cs_user_info'] = {}
        new['cs_username'] = None
    if 'cs_handler' in new:
        del new['cs_handler']
    new['cs_content'] = (
        '<pre>CAT-SOOP could not find the specified file or resource:\n'
        '%r</pre>') % (new['cs_original_path'])
    new['cs_original_path'] = ''
    e = ': <font color="red">404</font>'
    new['cs_header'] = new.get('cs_header', '') + e
    new['cs_content_header'] = 'File/Resource Not Found'
    new['cs_source_qstring'] = ''
    new['cs_top_menu_html'] = ''
    new['cs_breadcrumbs_html'] = ''
    s, h, o = dispatch.display_page(new)
    o = o.replace(new['cs_base_logo_text'], error_404_logo)
    return ('404', 'File Not Found'), h, o


error_404_logo = ("\   ???????? "
                "\n/    /\__/\  "
                "\n\__=(  @_@ )="
                "\n(__________) "
                "\n |_ |_ |_ |_ ")
"""This alternate logo replaces the CAT-SOOP logo on when a 404 (File Not
Found) error is encountered."""

error_500_logo = ("  _  _  _  _  "
                "\n  _|__|__|__| "
                "\n (  _     ___)"
                "\n=( x X  )=   \\"
                "\n  \/  \/     /"
                "\n             \\")
"""This alternate logo replaces the CAT-SOOP logo on when a 500 (Internal
Server Error) error is encountered."""
