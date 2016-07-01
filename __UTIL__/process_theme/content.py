# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.

import urllib.request

original_loc = cs_form.get('theme', 'BASE/themes/base.css')
temp = csm_dispatch._real_url_helper(globals(), original_loc)
if '__STATIC__' in temp:
    original_loc = csm_dispatch.static_file_location(globals(), temp[2:])
    with open(original_loc) as f:
        original_content = f.read()
else: # file must be remote
    try:
        original_content = urllib.request.urlopen(original_loc).read()
    except:
        original_content = 'Unknown theme: %r' % original_loc

cs_handler = 'raw_response'
content_type = 'text/css'

response = csm_language.handle_python_tags(globals(), original_content)
