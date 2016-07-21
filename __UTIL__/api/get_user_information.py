# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

# api endpoint to get user information.
# requires: username and password, or api token
# optional: course ID for extra information

import os
import json

login = csm_auth.get_auth_type_by_name(globals(), 'login')

user = None
error = None

if 'api_token' in cs_form:
    # if there is an API token, check it.
    user = csm_api.get_logged_in_user(globals())
    if user is None:
        error = "Invalid API token: %s" % cs_form['api_token']
else:
    if 'username' in cs_form and 'password_hash' in cs_form:
        # if no API token was given, but username and password were, check
        # those.
        uname = cs_form['username']
        pwd = cs_form['password_hash']
        hash_iters = globals().get('cs_password_hash_iterations', 250000)
        pwd_check = login.check_password(globals(), pwd, uname, hash_iters)
        if not pwd_check:
            error = 'Invalid username or password.'
        else:
            user = csm_logging.most_recent(None, uname, 'logininfo', None)
    else:
        error = 'API token or username and password hash required.'

if user is None and error is None:
    # catch-all error: if we haven't authenticated but don't have an error
    # messge, use this one.
    error = 'Could not authenticate' 

if error is None and 'course' in cs_form:
    # if we have successfully logged in and a course is specified, we need to
    # look up extra information from the course in question.
    course = cs_form['course']
    base_loc = os.path.join(cs_data_root, 'courses', course)
    if os.path.isdir(base_loc):
        uname = user['username']
        user = csm_auth._get_user_information(globals(), user,
                                              course, uname, do_preload=True)
    else:
        error = 'No such course: %s' % course

    

if error is not None:
    response = {'ok': False, 'error': error}
else:
    response = {'ok': True, 'user_info': user}

cs_handler = 'raw_response'
content_type = 'application/json'
response = json.dumps(response)
