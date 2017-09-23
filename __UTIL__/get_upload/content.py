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
import mimetypes

path = cs_form.get('path', None)
fname = cs_form.get('fname', None)

cs_handler = 'raw_response'

error = None
if path is None or fname is None:
    error = 'Please specify a path and a filename'

if error is None:
    try:
        fname = os.path.basename(fname)
        path = [i for i in json.loads(path) if i not in ('..', '.')]
    except:
        error = 'Could not interpret path and/or filename.'

if error is None:
    try:
        loc = os.path.join(cs_data_root, '__LOGS__', '_uploads', *path, fname)
        content_type = mimetypes.guess_type(fname)[0] or 'text/plain'
        with open(loc, 'rb') as f:
            response = f.read()
    except:
        error = 'There was an error retrieving the file.'

if error is not None:
    response = error
    content_type = 'text/plain'
