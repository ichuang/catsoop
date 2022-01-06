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

import os
import sys

from catsoop.wsgi import application
from cheroot import wsgi

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
print("[werkzeug_server] CATSOOP_LOC=%s" % CATSOOP_LOC)

from werkzeug.serving import run_simple
from catsoop.wsgi import application
from werkzeug.serving import make_ssl_devcert

host = sys.argv[2]
port = int(sys.argv[1])

kfn = '/tmp/catsoop_ssl_key'
make_ssl_devcert(kfn, host=host)

run_simple(host, port, application, use_reloader=False, ssl_context=(f'{kfn}.crt', f'{kfn}.key'))
