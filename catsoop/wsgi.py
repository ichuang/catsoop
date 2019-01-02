# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
WSGI Interface to CAT-SOOP
"""

import os
import sys

try:
    from . import dispatch
except:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
    import catsoop.dispatch as dispatch


def _ensure_bytes(x):
    try:
        return x.encode()
    except:
        return x


def application(environ, start_response):
    """
    WSGI application interface for CAT-SOOP, as specified in
    [PEP 3333](http://www.python.org/dev/peps/pep-3333/).
    """
    status, headers, content = dispatch.main(environ)
    start_response("%s %s" % (status[0], status[1]), list(headers.items()))
    if isinstance(content, (str, bytes)):
        return [_ensure_bytes(content)]
    else:
        return (_ensure_bytes(i) for i in content)
