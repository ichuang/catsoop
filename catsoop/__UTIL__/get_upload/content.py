# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

id_ = cs_form.get("id", None)
cs_handler = "raw_response"

error = None
if id_ is None:
    error = "Please specify an upload ID"

if error is None:
    try:
        info, response = cslog.retrieve_upload(id_)
    except:
        error = "Could not retrieve upload %r" % id_

if error is None:
    try:
        content_type = mimetypes.guess_type(info["filename"])[0] or "text/plain"
    except:
        error = "Could not determine appropriate MIME type"

if error is not None:
    response = error
    content_type = "text/plain"
