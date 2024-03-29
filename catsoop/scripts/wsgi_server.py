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

PORT_NUMBER = int(sys.argv[1])

CATSOOP_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
print("[wsgi_server] CATSOOP_LOC=%s" % CATSOOP_LOC)

addr = "0.0.0.0", PORT_NUMBER
# addr = "127.0.0.1", PORT_NUMBER
server = wsgi.Server(addr, application)
server.start()
