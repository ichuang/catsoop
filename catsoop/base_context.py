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

cs_version = '10.0.0-develop'
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

cs_url_root = 'http://localhost:3000'
"""
The URL root (without trailing slash).  Going to this URL should lead the user
to CAT-SOOP's information page.
"""

cs_auth_type = 'login'
"""
Which authentication type to use ('login' to use a form, 'cert' to read client
certificates).
"""

cs_log_type = 'rethinkdb'
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

cs_icon_url = 'data:image/gif;base64,R0lGODlhEAAQAKEAAAAAAAAzZv///wAAACH5BAEKAAMALAAAAAAQABAAAAI+nBdpGTdwWnQPQOSYsUBAmT1e9ymIQnYedaiWMHKyq8L2bb/4rfc17Bp5gDziK5gz0nY+nMyp2/EgsypnUAAAOw=='
"""
Special: A URL pointing to the page's favicon
"""

cs_loading_image = 'data:image/gif;base64,R0lGODlhEAAQAPIAAP///wAAAMLCwkJCQgAAAGJiYoKCgpKSkiH/C05FVFNDQVBFMi4wAwEAAAAh/hpDcmVhdGVkIHdpdGggYWpheGxvYWQuaW5mbwAh+QQJCgAAACwAAAAAEAAQAAADMwi63P4wyklrE2MIOggZnAdOmGYJRbExwroUmcG2LmDEwnHQLVsYOd2mBzkYDAdKa+dIAAAh+QQJCgAAACwAAAAAEAAQAAADNAi63P5OjCEgG4QMu7DmikRxQlFUYDEZIGBMRVsaqHwctXXf7WEYB4Ag1xjihkMZsiUkKhIAIfkECQoAAAAsAAAAABAAEAAAAzYIujIjK8pByJDMlFYvBoVjHA70GU7xSUJhmKtwHPAKzLO9HMaoKwJZ7Rf8AYPDDzKpZBqfvwQAIfkECQoAAAAsAAAAABAAEAAAAzMIumIlK8oyhpHsnFZfhYumCYUhDAQxRIdhHBGqRoKw0R8DYlJd8z0fMDgsGo/IpHI5TAAAIfkECQoAAAAsAAAAABAAEAAAAzIIunInK0rnZBTwGPNMgQwmdsNgXGJUlIWEuR5oWUIpz8pAEAMe6TwfwyYsGo/IpFKSAAAh+QQJCgAAACwAAAAAEAAQAAADMwi6IMKQORfjdOe82p4wGccc4CEuQradylesojEMBgsUc2G7sDX3lQGBMLAJibufbSlKAAAh+QQJCgAAACwAAAAAEAAQAAADMgi63P7wCRHZnFVdmgHu2nFwlWCI3WGc3TSWhUFGxTAUkGCbtgENBMJAEJsxgMLWzpEAACH5BAkKAAAALAAAAAAQABAAAAMyCLrc/jDKSatlQtScKdceCAjDII7HcQ4EMTCpyrCuUBjCYRgHVtqlAiB1YhiCnlsRkAAAOwAAAAAAAAAAAA=='
"""
A URI pointing to an image to be used as a loading icon.
"""

cs_check_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAAZiS0dEAAAAAAAA+UO7fwAAAAlwSFlzAABJ0gAASdIBqEWK+AAAAAl2cEFnAAAAFgAAABYA3MXpWAAAA5NJREFUOMu1lF1MFFcUx/8zd2d2Z9bZXT66wGJdpUhFGgUfVgs1QTEqGrVpTEx40JgmfepHeKjUPvHSEtukLzVN2qZt0qd+pn0hJm2pZAkU2hIB0S0KqLtsUXaXZWd2Zndm56MvQAZEbTfpTf45ufee+7vnnnvuBf6nRhW7sO1NAQ4XDV01YfAS+rvXztPFQJ/vBCxiHYRBLTJOxxid49sPdLnX+JBiwE1HwZuWK9zVcam8uaGtci4ZPamo0tlgiAzcGSo8KDrinCZ07322xSu4XVCtGF5/6W3hxRfO7GBdzo+LTkXrRWGH08G9ejh0ynU3MYyEOIOcJuL6zLhSMPVvigK3vwawNP3FsX2nnIq2gIxyH2XuWkxFJ63p+M24zoofFgUuCO4Ov6dqV32wgZ5bnICD5sE5yvB9+CtVN81z/d3Q/zO4vbvUQ8Nx+XjzCf5BZgpaIQe/UIfw2C+qqmW/7euRfrP7O+ydlgvlCNxJktkSGKOfrAUbmvF+Y+0ejueciCYn4eEqsCRJGI4MaYZlda4PZDXi1gvcZo5o8+naTUppiecN2B7Pobf4JkLYs6H6kOvv9A1YFuDlArgy3KsYltHZ1yOl1oMpADjUVeIFMUZbd7Vu3Vq1jVwZ6ZUTS8k/DRTO7GflxJDmHT/QeHBnwF9Kp6S7KBOCiCfSZv/Yr9d/eifTBMDaMGJCzB8an9ldHawKEDEXw7F9R9x76hqbCZi/wjn3j6WespotlQE6Kd0DoZ0wLRYDEwNaQdfPbQRdzbFpWQ28y8kaho68moWcj6C2ejNT4XvK1z82eLzlub30ohSDXijA56nGyOTveVPXPrt6SR5/1GUTAKhpZnrjqfmjGVnkghU1jGnqyCj3wTA06oN1lGEqyOZTcLECRFnF6K1romywJ2KDivZY8Oyglny6Tf1UlrTg7Hy0rrKkguWdbsj5NOR8GmpBBkCBY3wIT4zIOU19Jfze0rXHledD32bbxU2nCUU+3xnczm/x+4miijBMDZzTi7mFlB6JTQ///K64/0l1/9AD6evJfgcNu2/em4qMRCYUgAFDOORVFZHYtG7mrZfxL/5xskHfMTOkyotx7UvfNrN8LrXQIPA8cysWy0lZ9aOrH0i9ANhlOZbXUMtarRDKZslGCp3nDnv8zGWYuP3H12JHJoocAOMJsuxHopdhdmvXiq8FwFwnY519ZK4o22aUTStgy7bBytia9g/AJIpkBxWbzgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxMC0wMS0xMVQwOToxMzowNC0wNzowMJa4FNkAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTAtMDEtMTFUMDk6MTM6MDQtMDc6MDDn5axlAAAANHRFWHRMaWNlbnNlAGh0dHA6Ly9jcmVhdGl2ZWNvbW1vbnMub3JnL2xpY2Vuc2VzL0dQTC8yLjAvbGoGqAAAABN0RVh0U291cmNlAEdOT01FLUNvbG9yc6qZROIAAAAxdEVYdFNvdXJjZV9VUkwAaHR0cDovL2NvZGUuZ29vZ2xlLmNvbS9wL2dub21lLWNvbG9ycy9QHbXrAAAAAElFTkSuQmCC'
"""
A URI pointing to an image to be used for the "check" (correct) image.
"""

cs_cross_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAA3XAAAN1wFCKJt4AAAACXZwQWcAAAAWAAAAFgDcxelYAAADzklEQVQ4y7WVPU8bWRSG3zvjGdt3bMM62J5gZ+NAA6JIEykSCRnbVDRUW/AHtt9i22i77fIX0i7FVtNsEwWPSIpIaYIUFCmKQgJsGBuDPR4PHs/92MI2C9gpc6Wj+dB7nnvmPfdoiJQSP2IpP4QKIHbzRb1ajWmdzjYARDMzW5WdHTYtsV6txjTP24aUU3XKTTE5O7MT+fxGolDYUM7O7Hq1OnVzpd22E6a5kSgUNsgUnXIN2mrZqUKhUqpWaWl9nRrz8xXSal1LGusM06zcqdVoaX2dpkxzQkfGzdtZWfnbyOU2fq7VKDs/B1EUqLkcjl6+vPCOj+tKPr8JAGg07FSpVCnVaknebAJSQs1mcfjiReA3Gv9U37//5brHQgBCQEQR5Dg4R3FtLSkdx+oeHdkAkC6VrNLaWpKdnED2+yCaBjEYQHI+ZNy0gpjmVsd1nUPHCdRMBlAUCN8Hc12UVldpulh8ki4Wn5RWVylzXQjfBxQFSjqNw52doOO6DjHNrQkrAKBOSCxaWLBThYJ159EjKtptIIpAdB1qNgsA4OfnkGEIoutQZmfx9fXrwHddR/v0abMiJZsKHsPDcnkIf/iQCs+DjCIQTQOA4b2uDyt98ybwXdeJHxxcg04Fj+EXd+/amUJhrfjgQYq32wDnw4RYDMrMDI7fvvU9191NfvkyAZ06IOMlGYNgDHwwAI+i/8FCQA4GEIxBMva99OlW+Ldv28atW9b8/ftUBAHAOYiqDjfkHCQWA0km8e+7d0Gv1XJS375NVK3chHbzeTuRyVj5pSUaeR54vw8hJaSmQWoahJRgFxdgnof88jJNZDJWN5+364TEplZcJyTmzc3ZidlZy1xepnJ0NhVVBUkk0PjwwQeA/NJSSobh0AZVBYnHcbK/H/TbbSdzenpZ+WXF7Wx2WzcMa+7ePcp8H6zfhxQCHMDx3l7QbTZ3u83m7vHeXsClhBACPAzBul3kFhaobhhWO5vdnmieEAKcMfAwhBQChBBIAM2PH4O+5zk/dTqbAHDOuX2yv2/lFhepHDUUnEMwBjF+vmnFaTptxw3DypXLlBCC5sFB0Pd9Z67bvfzEsS6RSlm5cpkCQOPz5yDs9a7pJiavSakdNwwLAC56vVd/BsHWHiAAkPFJXAHUp5T+lTSMxwAw6PWcuSCYPnmEEB2AvgjQP+Lx5wJQfg/D304BdWSZOoILADwLiGfx+DMFEE/D8NevQABgAGAgpWRXwSoAHUB8dNUBaFdCvVI1BxBdiQGA/igiKaUg3/uZEkLICERGp+fSiishAEBOgfwHrlwiLshhIVcAAAAldEVYdGRhdGU6Y3JlYXRlADIwMTAtMDItMTdUMDc6MTI6MjctMDc6MDAAloH6AAAAJXRFWHRkYXRlOm1vZGlmeQAyMDEwLTAxLTExVDA5OjEzOjA0LTA3OjAw5+WsZQAAADR0RVh0TGljZW5zZQBodHRwOi8vY3JlYXRpdmVjb21tb25zLm9yZy9saWNlbnNlcy9HUEwvMi4wL2xqBqgAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtzY2FwZS5vcmeb7jwaAAAAE3RFWHRTb3VyY2UAR05PTUUtQ29sb3JzqplE4gAAADF0RVh0U291cmNlX1VSTABodHRwOi8vY29kZS5nb29nbGUuY29tL3AvZ25vbWUtY29sb3JzL1AdtesAAAAASUVORK5CYII='
"""
A URI pointing to an image to be used for the "cross" (incorrect) image.
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


# WebSockets

cs_checker_websocket = 'ws://localhost:3001'

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
