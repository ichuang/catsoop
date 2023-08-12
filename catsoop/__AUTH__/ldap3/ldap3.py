# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

import ldap3
from catsoop.__AUTH__.login.login import _get_base_url
from ldap3.core.exceptions import LDAPException


def get_logged_in_user(context):
    """
    Entry point for the authentication manager. This authentication
    manager expects a variable to be present in either the global
    "config.py" file or the "preload.py" file of the given subject.
    The variable should be a dictionary named "cs_ldap3" and contain
    two additional dictionaries under the keys "server" and "search".
    The "server" dictionary should contain the parameters needed to
    connect to the LDAP server, as used by the ldap3 library. At the
    minimum one should specify the "host" parameter. The "search"
    dictionary expects the keys "filter", "base" and "attributes". The
    "filter" parameter should contain the filter for the search
    request, e.g. "(uid={})", where "{}" will be replaced by the
    username at login. "base" should be the search base e.g.
    "dc=example,dc=com". "attributes" should be a dictionary containing
    the keys "name" and "email", for which the values should be the
    strings containing the name of the LDAP attributes containing the
    full name and email of the user. See the documentation for an
    example and more in-depth information.

    :param context: The request context
    :return: A dictionary containing either information about the
             logged in user or about actions that should be taken in
             regards to authentication (such as redirects, etc.).
    """
    session = context["cs_session_data"]
    action = context["cs_form"].get("loginaction", None)

    if action == "logout":
        # Reset all parameters at logout
        context["cs_session_data"] = {}
        return {"cs_reload": True}
    elif "username" in session:
        # If the username exists in the session, then the user is
        # already logged in, and we can simply return the data.
        username = session["username"]
        return {
            "username": username,
            "name": session.get("name", username),
            "email": session.get("email", username),
        }

    if action == "login":
        return login(context)
    elif action is None:
        return setup_login_boxes(context)
    return {}


def login(context):
    """
    Helper method for handling login. If there is a login form in the
    request, the method tries to log in with the given username and
    password. If the login succeeds, information about the user is
    returned. Otherwise the content of the page is modified such that
    a login form is shown.

    :param context: The request context
    :return: Either the user details of a command to render the login
             form
    """
    username = context["cs_form"].get("login_username", "")
    password = context["cs_form"].get("login_password", "")
    error_message = ""
    login_message = context.get("cs_ldap3_login_message", "")

    if username and password:
        # Retrieves the "cs_ldap3" configuration.
        ldap3_config = context["csm_base_context"].cs_ldap3

        try:
            server = ldap3.Server(**ldap3_config["server"])
            conn = ldap3.Connection(server, auto_bind=True)
        except LDAPException as exception:
            return login_render(
                context, username, "Could not connect to login server", login_message
            )

        request = ldap3_config["search"]["filter"].format(username)
        email_attribute_name = ldap3_config["search"]["attributes"]["email"]
        name_attribute_name = ldap3_config["search"]["attributes"]["name"]
        conn.search(
            ldap3_config["search"]["base"],
            request,
            attributes=[email_attribute_name, name_attribute_name],
        )

        # The LDAP may return several users.
        for user_data in conn.response:
            if conn.rebind(user_data["dn"], password=password):
                try:
                    info = {
                        "username": username,
                        "name": user_data["attributes"][name_attribute_name][0],
                        "email": user_data["attributes"][email_attribute_name][0],
                    }
                    context["cs_session_data"].update(info)
                    info["cs_reload"] = True
                    return info
                except (KeyError, IndexError):
                    # If the attributes do not exist, just skip and
                    # continue to the next user.
                    pass

        error_message = "Username or password is incorrect."

    return login_render(context, username, error_message, login_message)


def login_render(context, username, error_message="", login_message=""):
    """
    Helper method to create the rendering of the login page.

    :param context: The request context
    :param username: The username to autofill in the "username" field
    :param error_message: An optional error_message
    :param login_message: An optional message to provide users with
                          information about how to log in, e.g., what
                          type of credentials to use.
    :return:
    """
    context["cs_content"] = LOGIN_FORM.format(
        username=username, error_message=error_message, login_message=login_message
    )
    context["cs_content_header"] = "Please Log In To Continue"
    return {"cs_render_now": True}


def setup_login_boxes(context):
    """
    A helper method to add informative login boxes to the top of the
    current page. Either adds a login boxes telling the user to login
    in to get the full experience of the site or in the case of a page
    that requires authentication replaces the content of the page with
    a box telling the user to log in.

    :param context: The request context
    :return: A dictionary containing information about what CAT-SOOP
             should do next.
    """
    if context.get("cs_view_without_auth", True):
        # Add a box to the top of pages that do not require
        # authentication, telling users that they should log in to get
        # the full experience of the site.
        old_post_load = context.get("cs_post_load", None)

        # Redefine post load function, as to add a login box to the top
        # of the page while still keeping the content of the page.
        def new_post_load(context):
            if old_post_load is not None:
                old_post_load(context)

            if "cs_login_box" in context:
                login_box = context["cs_login_box"](context)
            else:
                login_box = LOGIN_BOX.format(_get_base_url(context))

            context["cs_content"] = "%s\n\n%s" % (login_box, context["cs_content"])

        context["cs_post_load"] = new_post_load
        return {}
    else:
        # Replace pages that require authentication with a message
        # telling them to log in to see the content of the page.
        context["cs_handler"] = "passthrough"
        context["cs_content_header"] = "Please Log In"
        context["cs_content"] = LOGIN_PAGE.format(_get_base_url(context))
        return {"cs_render_now": True}


# HTML to display when an anonymous user tries to access a page that
# requires the user to be logged in.
LOGIN_PAGE = """
<div id="catsoop_login_box">
    <b><center>You are not logged in.</center></b> <br/>
    Access to this page requires logging in. Please <a
    href="{}?loginaction=login">Log In</a> to continue.
</div>
"""

# HTML box to display at the top of the page when the user is not
# logged in.
LOGIN_BOX = """
<div class="response" id="catsoop_login_box">
    <b><center>You are not logged in.</center></b><br/>
    Please <a href="{}?loginaction=login">Log In
    </a> for full access to the web site.
</div>
"""

# HTML for the login form.
LOGIN_FORM = """
<center>
    <form method="POST">
        <p>{login_message}</p>
        <p style="color: red">{error_message}</p>
        <table>
            <tr>
                <td>Username:</td>
                <td>
                    <input type="text" name="login_username" id="login_username"
                     value="{username}" placeholder="Username"/>
                </td>
            </tr>
            <tr>
                <td>Password:</td>
                <td>
                    <input type="password" name="login_password"
                     id="login_password" placeholder="Password"/>
                </td>
            </tr>
            <tr>
                <td></td>
                <td>
                    <input type="submit" class="btn" value="Log In"
                     style="float: right"/>
                </td>
            </tr>
        </table>
    </form>
</center>
"""
