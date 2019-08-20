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
"""
Methods related to authentication for API access
"""

import os
import uuid
import random
import string

_nodoc = {"CHARACTERS"}

CHARACTERS = string.ascii_letters + string.digits


def new_api_token(context, username):
    """
    Generate a new API token for the given user.

    **Parameters**:

    * `context`: the context associated with this request
    * `username`: the username for which a new API token should be generated


    **Returns:** a new API token for the given user, with length as given by
    `cs_api_token_length`.
    """
    length = context.get("cs_api_token_length", 70)
    seed = username + uuid.uuid4().hex
    r = random.Random()
    r.seed(seed)
    return "".join(r.choice(CHARACTERS) for i in range(length))


def initialize_api_token(context, user_info):
    """
    Intialize an API token for a user, and store the association in the
    database.

    **Parameters:**

    * `context`: the context associated with this request
    * `user_info`: the user_info dictionary associated with this request
        (should ideally contain `'username'`, `'name'`, and `'email'` keys).

    **Returns:** the newly-generated API token
    """
    user_info = {
        k: v for (k, v) in user_info.items() if k in {"username", "name", "email"}
    }
    token = new_api_token(context, user_info["username"])
    context["csm_cslog"].overwrite_log("_api_tokens", [], str(token), user_info)
    context["csm_cslog"].update_log("_api_users", [], user_info["username"], token)
    return token


def userinfo_from_token(context, tok):
    """
    Given an API token, return the associated user's information.

    **Parameters:**

    * `context`: the context associated with this request
    * `tok`: an API token

    **Returns:** a dictionary containing the information associated with the
    user who holds the given API token; it will contain some subset of the keys
    `'username'`, `'name'`, and `'email'`.  Returns `None` if the given token
    is invalid.
    """
    return context["csm_cslog"].most_recent("_api_tokens", [], str(tok), None)


def get_logged_in_user(context):
    """
    Helper function.  Given a request context, returns the information
    associated with the user making the request if an API token is present.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** a dictionary containing the information associated with the
    user who holds the given API token; it will contain the key `api_token`, as
    well as some subset of the keys `'username'`, `'name'`, and `'email'`.
    """
    form = context.get("cs_form", {})
    if "api_token" in form:
        tok = form["api_token"]
        log = userinfo_from_token(context, tok)
        if log is not None:
            log["api_token"] = tok
            return log
    return None


def get_user_information(
    context, uname=None, passwd=None, api_token=None, course=None, _as=None
):
    """
    Return the information associated with a user identified by an API token or
    a username and password.

    **Parameters:**

    * `context`: the context associated with this request

    **Optional Parameters:**

    * `uname`: if logging in via password, this is the username of the user in
        question.
    * `passwd`: if logging in via password, this is the hex-encoded 32-bit
        result of hashing the user's password with pbkdf2 for 100000 iterations,
        with a salt given by the username and the password concatenated
        together.  this is not the user's password in plain text.
    * `api_token`: if logging in via API token, this is the token of the person
        making the request.
    * `course`: if given, relevant user information from that course (section,
        role, permissions, etc) will be included in the result
    * `_as`: if making this request to get someone else's information, this is
        the other person's username.  must have relevant permissions.

    **Returns:** a dictionary with two keys. `'ok'` maps to a Boolean
    indicating whether the lookup was successful.

    * If `'ok`' maps to `False`, then the additional key is `'error'`, which
        maps to a string containing an error message.
    * If `'ok`' maps to `True`, then the additional key is `'user_info'`, which
        maps to a dictionary containing the user's information.
    """
    login = context["csm_auth"].get_auth_type_by_name(context, "login")

    user = None
    error = None

    log = context["csm_cslog"]
    if api_token is not None:
        # if there is an API token, check it.
        user = userinfo_from_token(context, api_token)
        if user is None:
            error = "Invalid API token: %s" % api_token
        else:
            user["api_token"] = api_token
            extra_info = log.most_recent("_extra_info", [], user["username"], {})
            user.update(extra_info)
    else:
        if uname is not None and passwd is not None:
            # if no API token was given, but username and password were, check
            # those.
            hash_iters = context.get("cs_password_hash_iterations", 500000)
            pwd_check = login.check_password(context, passwd, uname, hash_iters)
            if not pwd_check:
                error = "Invalid username or password."
            else:
                user = log.most_recent("_logininfo", [], user["username"], None)
        else:
            error = "API token or username and password hash required."

    if user is None and error is None:
        # catch-all error: if we haven't authenticated but don't have an error
        # messge, use this one.
        error = "Could not authenticate"

    if error is None and course is not None:
        # if we have successfully logged in and a course is specified, we need to
        # look up extra information from the course in question.
        ctx = context["csm_loader"].generate_context([course])

        ctx["cs_form"] = {}
        if _as is not None:
            ctx["cs_form"]["as"] = _as

        base_loc = os.path.join(context["cs_data_root"], "courses", course)
        if os.path.isdir(base_loc):
            uname = user["username"]
            ctx["cs_user_info"] = user
            user = context["csm_auth"]._get_user_information(
                ctx, user, course, uname, do_preload=True
            )
        else:
            error = "No such course: %s" % course

    if error is not None:
        return {"ok": False, "error": error}
    else:
        return {"ok": True, "user_info": user}
