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
Initial context for page loads, including initializing 'special' variables

Many of the variables in this file are special variables that affect the way
the page is rendered (these special variables can be overwritten by early loads
or late loads at lower levels).
"""

_nodoc = {
    "contents",
    "cs_all_pieces",
    "cs_all_thirdparty",
    "f",
    "i",
    "root",
    "cs_dummy_username",
    "datetime",
}

cs_version = "(development version, v13.0.0+)"
"""
CAT-SOOP's version number
"""

cs_fs_root = "/home/cat-soop/cat-soop"
"""
The directory where CAT-SOOP's source is located (no trailing slash).
"""

cs_data_root = r"/home/cat-soop/data"
"""
The directory where CAT-SOOP's data files are located (no trailing slash).
"""

cs_url_root = "http://localhost:6010"
"""
The URL root (without trailing slash).  Going to this URL should lead the user
to CAT-SOOP's information page.
"""

cs_auth_type = "login"
"""
Special: Which authentication type to use (`'login'` to use a form, `'cert'` to
read client certificates, `'openid_connect'` to use OpenID Connect, or some
other value for a course-specific or other custom authentication type).
"""

# Default Page Content
cs_title = "CAT-SOOP"
"""
Special: The page title, to be displayed in the browser's title bar
"""

cs_base_logo_text = (
    "\            "
    "\n/    /\__/\  "
    "\n\__=(  o_O )="
    "\n(__________) "
    "\n |_ |_ |_ |_ "
)
"""
Special: Text representing the CAT-SOOP Logo
"""

cs_main_page_text = ""
"""
Special: Text to be added to the main (information) page when no course is
chosen.
"""

cs_base_color = "#0000CC"
"""
Special: The base color to use to customize the main theme, hexadecimal format.
"""

cs_light_color = None
"""
Special: Light version of the color in the main theme, hexadeciaml format.  If
value is `None`, an appropriate color will be computed based on
`cs_base_color`.
"""

cs_process_theme = True
"""
Special: Whether the theme should be "processed" by, e.g., evaluating Python
code
"""

cs_welcome_message = ""
"""
Special: Welcome message displayed next to the title in base theme.
"""

cs_header = "CAT-SOOP"
"""
Special: The main header, displayed at the top-left of the page in the base
theme.
"""

cs_subheader = ""
"""
Special: Sub-header, displayed below the main header
"""

cs_footer = ""
"""
Special: Footer, displayed in addition to the "powered by CAT-SOOP" link
"""

cs_top_menu = ""
"""
Special: Navigation menu.

The navigation menu is specified as a string (containing raw HTML), or as a list of dictionaries.

Each dictionary should contain two keys:

* `'text'` maps to the text to be displayed, and
* `'link'` maps to a URL, or to another list of dictionaries representing a
    submenu.

In the case where a dictionary is specified, the appropriate HTML for use with
the base theme will be generated.
"""

cs_scripts = ""
"""
Special: HTML to import additional scripts; included in the page's <head> tags
"""

cs_side_menu = ""
"""
Special: Additional menu space
"""

cs_bottom_menu = ""
"""
Special: Additional menu space
"""

cs_content_header = (
    '<span class="cs_base_bold">C</span>AT-SOOP is an '
    '<span class="cs_base_bold">A</span>utomatic '
    '<span class="cs_base_bold">T</span>utor<br/> for '
    '<span class="cs_base_bold">S</span>ix-'
    '<span class="cs_base_bold">O</span>h-'
    '<span class="cs_base_bold">O</span>ne '
    '<span class="cs_base_bold">P</span>roblems'
)
"""
Special: The text to be displayed at the top of the "content" block.
"""

cs_content = ""
"""
Special: The content of the page
"""

cs_footnotes = ""
"""
Special: A string containing footnotes, if any.  Automatically populated by the
default handler.
"""

cs_template = "BASE/templates/main.template"
"""
Special: The template file to use to render the page
"""

# Default Look and Feel

cs_theme = "BASE/themes/base.css"
"""
Special: A URL pointing to the page's CSS stylesheet
"""

cs_icon_url = "data:image/gif;base64,R0lGODlhEAAQAKEAAAAAAAAzZv///wAAACH5BAEKAAMALAAAAAAQABAAAAIynI85oL3A3IFARFehlcvW3XyaR5XiJ6Tqmo6sOsZoS2viets0XJ+vzCoFXS8Yw4SkDAoAOw=="
"""
Special: A URL pointing to the page's favicon
"""

cs_loading_image = "data:image/gif;base64,R0lGODlhEAAQAPIGAMLCwkJCQgAAAGJiYoKCgpKSkv///wAAACH/C05FVFNDQVBFMi4wAwEAAAAh/hpDcmVhdGVkIHdpdGggYWpheGxvYWQuaW5mbwAh+QQJCgAGACwAAAAAEAAQAAADMmi63P4wyklrAyEAGoQInAdOmGYBw7AxwLoMGcG2rkHEQFHQLTsQOd2mB9ERCpTWzpEAACH5BAkKAAYALAAAAgAKAA4AAAMraAYRoNAEIUJUs97VHgTD4EVDQ2xEM2wgMV5AUbyKLKNEvoxA3P8sYNCQAAAh+QQJCgAGACwAAAAACgAOAAADLWi6EAFrBSGCAmQ0as1wROFABuEM0TUQ5FUU7fK+aRkWNYDFqV4bOl8v+BMuEgAh+QQJCgAGACwAAAAADgAKAAADKmi6QAMrrhECkaaVVl+FRiFuAwEEghAoYxGhqgI0oPxlNSbPOcb3PqAkAQAh+QQJCgAGACwCAAAADgAKAAADKWhqUAUrLuekApA+MiDD4BYExAVGwzgsmNR0lgWMXmwEghDYCq7zDFoCACH5BAkKAAYALAYAAAAKAA4AAAMqaADWros9GEuRUBE7jeUTYGEhMZANEQREN6xDJ54PsKJGIAhBp/OyWyMBACH5BAkKAAYALAYAAgAKAA4AAAMpaKoA+609Fie1C5Tipt7WRhRWw0ED0T1DEAyMq7mEEghCAKTdnZcySwIAIfkEBQoABgAsAgAGAA4ACgAAAytoumwALb4X2YR1URACVkBRYIEgBIw4KuUJDERIzGD3doMhfguBZyAYT5EAADs="
"""
A URI pointing to an image to be used as a loading icon.
"""

cs_check_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAMAAADzapwJAAABQVBMVEUAAAAGDQAAAAAAAAAAAAAAAAAAAACGqlBIfBNciiZGeg9Eeg5Feg5Gew9CdgpCdgxDehJvmDN1nj9plTVWhRtOgRlMfxZjkS5Geg9EeA5Geg5HfBBHew5GeQ5Cdg1CeAxDegtHgACVtmV+pURPgBp4oEBEeQx+o0p8oklFeg5YiCJIfRFEdQ5GehBHeg9CdwtEdQxEeg5Fdw5DeQ1Eegs2YQlCdwpCeAxDeQ0PHgBGdA9AdgkAAAAAAAARIgChwGKPs0qjwXKStUyFqD6CqDfJ3p+91Ji00XqlwmypyGihwGiauluWtlicwFKXulGTuEmMr0WOs0OKr0CGrDuEqjrR46zC2Ji+1ZC804640oK1z4CxzHywynqsx3enw3WYuWidvF+fwlqgxFePsFWSs1KIrE2Wu0uOr0qGqkeCpj50nDHRgoCJAAAAP3RSTlMABA0HEgoQ/ff17+jbxi8nDvz39vb29fTy7dPQoJeLVRUJ/f39+vn49/f118jAvrKWcW9jWllJQjkiIRwZFg8RajNxAAAA+klEQVQY06XQ1bLCMBAGYNJCHXfnuLtrFXc5gru+/wMQhhZouWRvMvNt/kx2dbvUC+V/3tY9OhZzX5i0HDqNxn/aRo2aXb/JXtR+p2HjfjUb5xmg1kfyL9v9d76q1UK1kqPaSWAFy1TQVs+zvCci4wd9fA8PE9HM5Rvkg5JlcJ68iuh8OFtkcb/ywrUtlUscUTfniaKQIlaj0AdsoZTuH2aEUsceXM/AuNNcmcsIZW7otWwsIuCacBVJqgycYdWPwx7rWJQKVu0y3n0OUZyemVUIAPp9S8wcIQRBDCgAsqIGBNM/eS/fPr/02KKx5IXDBixsfV2OwCYERebVjyGAvqhE3QAAAABJRU5ErkJggg=="
"""
A URI pointing to an image to be used for the "check" (correct) image.
"""

cs_cross_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAMAAADzapwJAAAA0lBMVEUAAAC/AAC/QEAAAADALS2qCwsAAAAAAAC7Jia3Hx+zGRm4ICCxFBTKQkLJPj68JycEAADMRUXMSEixFRXENjahBwe+KSmuEBDEMTEIAAALAAANAAAAAADGOTm+LCzCMjK1GxuzGRmuDw8AAAAsAADMR0fMSkrEMjLNQEDjbm7gYGDYUVHPRkbKPT3iZGTng4PmfHzld3fkcnLiZmbeW1vVVVXUTU3SSEjIODjpi4voiIjiamrfamrcZGTYW1vcV1faVVXST0/WTk7RTU3QRETlfn4RycE0AAAAKHRSTlMABAQEtrcvD/X19ba29fW2Kvb19fS2rKysJhsWCvX187a2tiER9vWsKh9QBQAAAP9JREFUGNOVzNdygkAYhuEsSChSVSxg1yQsvSliN+r935KL++N46jc7y8vDDF+fj+n3Gai/qqAbP60GQ+u3KlBjW5K3qlplaYB31QinW0Njqu9pGild4HiX4UjRNCXCGb6rlBlNTbJwFytKjMlD1eDnqDlKQzdMkoxcoyYiBN7Bbu6Sgzugte/z0ynfg9Y8nRzOnnc+TKboTWfjo/fvkXMcz9BLZWG1Ltar5yXI6KVX/1ZcBOFS3Pxr7T3RdxzHF2UZokdZCoLAEecIzUWHpEQZcdJmI3HorcDbbW7Jky2rAmWHtmkO9G8yXTdNix+ylHnbWjxdHywsm2cJw1i6Gh6M9B+39Tnr2wAAAABJRU5ErkJggg=="
"""
A URI pointing to an image to be used for the "cross" (incorrect) image.
"""


cs_course = None
"""
The course associated with the given request (should not be manually set)
"""

# Questions / Checker

cs_question_type_defaults = {}
"""
Special: A dictionary mapping question type names to dictionaries containing
default values to use for that question type.  These values are loaded in
before the values in a <question> tag are evaluated.
"""

cs_checker_websocket = "ws://localhost:6011"
"""
Special: The location to which the browser should connect to the checker's
"reporter" process.
"""

cs_checker_server_port = 6011
"""
Special: The local port on which the websocket server should run
"""

cs_checker_global_timeout = 120
"""
Special: The absolute maximum length (in seconds) that a checker should be
allowed to run before being killed.  This trumps any limits set by a particular
question so that if there is, for example, an infinite loop in a checker's
code, it will still be killed eventually.
"""

cs_checker_parallel_checks = 1
"""
Special: The number of checks the checker should run simultaneously.
"""

# UWSGI Server

cs_wsgi_server = "cheroot"
"""
The WSGI server to use.  Currently, must be 'cheroot' or 'uwsgi'
"""

cs_wsgi_server_port = 6010
"""
Special: The local port on which the WSGI server should run.
"""

cs_wsgi_server_min_processes = 1
"""
Special: The minimum number of worker processes the UWSGI server should have
running
"""

cs_wsgi_server_max_processes = 1
"""
Special: The maximum number of worker processes the UWSGI server should have
running
"""

# Log Encryption

cs_log_compression = False
"""
Special: Boolean indicating whether log entries should be compressed.
"""

cs_log_encryption = False
"""
Special: Boolean indicating whether log entries should be encrypted.
"""

# File Upload Type

cs_upload_management = "file"
"""
Special: defines how CAT-SOOP should handle file uploads.  Must be `'file'` or
`'db'`.

In `'file'` mode, CAT-SOOP will store the uploaded files on disk, under
`<cs_data_root>/__LOGS__/_uploads`.

In `'db'` mode, CAT-SOOP will store the contents of the files directly in the
CAT-SOOP logs.
"""

# Debugging Function

import os

from datetime import datetime

cs_debug_log_location = "/tmp/catsoop.log"
"""
The filename where the user debug log should be stored (via cs_debug)
"""


def cs_debug(*values, tag=""):
    """
    Write values to cs_debug_log_location, with a timestamp and an optional tag.
    If cs_debug_log_location is None, do nothing.
    """
    if cs_debug_log_location is None:
        return
    with open(cs_debug_log_location, "a") as myfile:
        print(datetime.now().time(), tag, *values, file=myfile)


_cs_config_errors = []

# try to import configuration from config.py

try:
    with open(os.path.join(os.path.dirname(__file__), "config.py")) as f:
        exec(f.read())
except Exception as e:
    _cs_config_errors.append("error in config.py: %s" % (e,))

# Import all CAT-SOOP modules/subpackages

cs_all_pieces = [
    "api",
    "auth",
    "base_context",
    "check",
    "cslog",
    "dispatch",
    "errors",
    "fernet",
    "groups",
    "language",
    "loader",
    "mail",
    "process",
    "session",
    "time",
    "thirdparty",
    "tutor",
    "util",
]

cs_all_thirdparty = ["data_uri"]

for i in cs_all_pieces:
    if i != "base_context":
        exec("from . import %s" % i)
        exec("csm_%s = %s" % (i, i))

exec("csm_tools = csm_thirdparty")

for i in cs_all_thirdparty:
    exec("from .thirdparty import %s" % i)
    exec("csm_thirdparty.%s = %s" % (i, i))

# Checks for valid Configuration

# check for valid fs_root
_fs_root_error = "cs_fs_root must be a directory containing the " "cat-soop source code"
if not os.path.isdir(cs_fs_root):
    _cs_config_errors.append(_fs_root_error)
else:
    root = os.path.join(cs_fs_root, "catsoop")
    if not os.path.isdir(root):
        _cs_config_errors.append(_fs_root_error)
    else:
        contents = os.listdir(root)
        if not all(("%s.py" % i in contents or i in contents) for i in cs_all_pieces):
            _cs_config_errors.append(_fs_root_error)
# check for valid data_root
if not os.path.isdir(cs_data_root):
    _cs_config_errors.append("cs_data_root must be an existing directory")
else:
    if not os.access(cs_data_root, os.W_OK):
        _cs_config_errors.append(
            "the web server must be able to write to " "cs_data_root"
        )
