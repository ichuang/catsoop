# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

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
