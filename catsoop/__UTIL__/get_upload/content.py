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

import json
import mimetypes

path = cs_form.get("path", None)
fname = cs_form.get("fname", None)

cs_handler = "raw_response"

error = None
if path is None or fname is None:
    error = "Please specify a path and a filename"

if error is None:
    try:
        fname = os.path.basename(fname)
        path = json.loads(path)
    except:
        error = "Could not interpret path and/or filename."

if error is None:
    # try:
    upload_dir = os.path.realpath(os.path.join(cs_data_root, "__LOGS__", "_uploads"))
    loc = os.path.realpath(os.path.join(upload_dir, *path, fname))
    assert loc.startswith(upload_dir)
    with open(os.path.join(loc, "info"), "rb") as f:
        content_type = (
            mimetypes.guess_type(csm_cslog.unprep(f.read())["filename"])[0]
            or "text/plain"
        )
    with open(os.path.join(loc, "content"), "rb") as f:
        response = f.read()
    if csm_cslog.ENCRYPT_KEY is not None:
        response = csm_cslog.decompress_decrypt(response)
# except:
#    error = 'There was an error retrieving the file.'

if error is not None:
    response = error
    content_type = "text/plain"
