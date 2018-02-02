# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hartz@mit.edu>
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

# api endpoint to get user information.
# requires: username and password, or api token
# optional: course ID for extra information

import json

cs_handler = 'raw_response'
content_type = 'application/json'

output = csm_api.get_user_information(globals(),
                                      uname=cs_form.get('username', None),
                                      passwd=cs_form.get('password_hash', None),
                                      api_token=cs_form.get('api_token', None),
                                      course=cs_form.get('course', None),
                                      _as=cs_form.get('as', None))

response = json.dumps(output)
