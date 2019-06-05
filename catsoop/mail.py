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
Methods for sending e-mail from within CAT-SOOP
"""

import re
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

_nodoc = {"MIMEText", "MIMEMultipart"}

RE_URL = re.compile(r"([^:]*:\/\/)?(([^\/]*\.)*([^\/\.]+\.[^\/]+)+)")
"""
Regular expression to match a URL, to give a chance at guessing a reasonable
default "from" address
"""


def get_from_address(context):
    """
    Get the address that should be used for the "From" field in sent e-mails

    If `cs_email_from address` is sent, use that.  Otherwise, if `cs_url_root`
    is a sensible URL, then use `"no-reply@%s" % cs_url_root`.  Otherwise,
    return `None`.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** a string containing a default "From" address, or `None` in the
    case of an error.
    """
    from_addr = context.get("cs_email_from_address", None)
    if from_addr is not None:
        return from_addr
    # no address specified.
    # try to figure out a reasonable guess from cs_url_root.
    m = RE_URL.match(context.get("cs_url_root", ""))
    if m is None:
        # cs_url_root not set, or didn't match RE_URL; return None
        # (will error out later)
        return None
    return "no-reply@%s" % m.group(2)


def get_smtp_config_vars(context):
    """
    Helper function.  Get the values of e-mail-related configuration variables
    from the given context.

    In particular, this function looks for `cs_smtp_host`, `cs_smtp_port`,
    `cs_smtp_user`, and `cs_smtp_password`.  If those values are not provided,
    the function assumes it is connecting to localhost on port 25, and that no
    username or password are required.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** a 4-tuple `(hostname, port, username, password)`
    """
    host = context.get("cs_smtp_host", "localhost")
    port = context.get("cs_smtp_port", 25)
    user = context.get("cs_smtp_user", None)
    passwd = context.get("cs_smtp_password", None)
    return host, port, user, passwd


def get_smtp_object(context):
    """
    Return an SMTP object for sending e-mails, or `None` if not configured to
    send e-mail.

    This function is actually also used as the primary means of detecting
    whether this instance is capable of sending e-mails (which controls certain
    behaviors, such as whether e-mail confirmations are required when signing
    up for an account under the `"login"` authentication type.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** an `smtplib.SMTP` object to use for sending e-mail, or `None`
    if this instance is not capable of sending e-mail.
    """
    host, port, user, passwd = get_smtp_config_vars(context)
    try:
        smtp = setup_smtp_object(smtplib.SMTP(host, port), user, passwd)
        return smtp
    except:
        return None


def setup_smtp_object(smtp, user, passwd):
    """
    Helper function.  Set up an `smtplib.SMTP` object for use with CAT-SOOP,
    enabling TLS if possible and logging in a user if information is specified.

    **Parameters**:

    * `smtp`: the `smtplib.SMTP` object to configure
    * `user`: the username to use when logging in
    * `password`: the password to use when logging in

    **Returns:** the same `smtplib.SMTP` object that was passed in, after
    configuring it.
    """
    smtp.set_debuglevel(False)
    smtp.ehlo()
    if user is not None and passwd is not None:
        if smtp.has_extn("STARTTLS"):
            smtp.starttls()
            smtp.ehlo()
        smtp.login(user, passwd)
    return smtp


def can_send_email(context, smtp=-1):
    """
    Test whether CAT-SOOP can send e-mail as currently configured

    **Parameters**:

    * `context`: the context associated with this request

    **Optional Parameters:**

    * `smtp` (default `-1`): the `smtplib.SMTP` object to use; if none is
        provided, `catsoop.mail.get_smtp_object` is invoked to create one

    **Returns:** `True` if this instance is capable of sending e-mails (if it
    properly configured an `smtplib.SMTP` object and has a valid "From"
    address), and `False` otherwise
    """
    if smtp == -1:
        smtp = get_smtp_object(context)
    return smtp is not None and get_from_address(context) is not None


def send_email(context, to_addr, subject, body, html_body=None, from_addr=None):
    """
    Helper function.  Send an e-mail.

    **Parameters**:

    * `context`: the context associated with this request
    * `to_addr`: A string containing a single e-mail address for the recipient,
        or an iterable containing multiple recipient addresses.
    * `subject`: A string representing the subject of the e-mail message
    * `body`: A string representing the contents of the e-mail (plain text)

    **Optional Parameters:**

    * `html_body` (default `None`): A string representing the contents of the
        e-mail in HTML mode, or `None` to send only a plain-text message
    * `from_addr` (default `None`): the "From" address to use; if none is
        provided, the result of `catsoop.mail.get_from_address` is used

    **Returns:** a dictionary containing error information
    """
    if not isinstance(to_addr, (list, tuple, set)):
        to_addr = [to_addr]
    if not can_send_email(context):
        return dict((a, None) for a in to_addr)
    msg = MIMEText(body, "plain")
    if html_body is not None:
        _m = msg
        msg = MIMEMultipart("alternative")
        msg.attach(_m)
        msg.attach(MIMEText(html_body, "html"))
    msg["To"] = ", ".join(to_addr)
    msg["From"] = _from = get_from_address(context) if from_addr is None else from_addr
    msg["Subject"] = subject
    smtp = get_smtp_object(context)
    try:
        smtp.sendmail(_from, to_addr, msg.as_string())
        out = {}
        smtp.close()
    except:
        out = dict((a, None) for a in to_addr)
    return out


def internal_message(context, course, recipient, subject, body, from_addr=None):
    """
    Send an e-mail to a member of a course.

    This function will send a multipart message.  The HTML portion will consist
    of the result of interpreting the given `body` as Markdown, and the
    plain-text portion will contain `body` verbatim.

    **Parameters**:

    * `context`: the context associated with this request
    * `course`: the course associated with this request (where to look for user
        information for the recipient)
    * `recipient`: the CAT-SOOP username (not e-mail address) of the indented
        recipient
    * `subject`: A string representing the subject of the e-mail message
    * `body`: A string representing the contents of the e-mail (plain text)

    **Optional Parameters:**

    * `from_addr` (default `None`): the "From" address to use; if none is
        provided, the result of `catsoop.mail.get_from_address` is used

    **Returns:** a dictionary containing error information (empty on success),
    or a string containing an error message.
    """
    if recipient not in context["csm_user"].list_all_users(context, course):
        return "%s is not a user in %s." % (recipient, course)
    into = {"username": recipient}
    ctx = context["csm_loader"].spoof_early_load([course])
    uinfo = context["csm_auth"]._get_user_information(ctx, into, course, recipient)
    if "email" not in uinfo:
        return "No e-mail address found for %s" % recipient
    email = uinfo["email"]
    lang = context["csm_language"]
    html_body = lang._md_format_string(context, body, False)
    return send_email(context, email, subject, body, html_body, from_addr)
