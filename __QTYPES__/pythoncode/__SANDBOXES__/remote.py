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

import json
import urllib.request, urllib.parse, urllib.error

SANDBOX_URL = 'https://catsoop.mit.edu/python3_sandbox'


def run_code(context, code, options):
    code = code.replace('\r\n', '\n')
    data = urllib.parse.urlencode({"code": code, "options": options}).encode()
    request = urllib.request.Request(
        context.get('csq_sandbox_url', SANDBOX_URL), data)
    try:
        resp = urllib.request.urlopen(request, data).read()
        resp = json.loads(resp.decode())
        out = resp['stdout']
        err = resp['stderr']
        fname = resp['filename']
    except:
        out = ''
        err = 'CAT-SOOP: Could not connect to %s' % SANDBOX_URL
        fname = ''
    return fname, out, err
