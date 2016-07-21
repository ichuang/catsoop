# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.
"""
Methods for sending e-mail from within CAT-SOOP
"""

import re
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

RE_URL = re.compile(r"([^:]*:\/\/)?(([^\/]*\.)*([^\/\.]+\.[^\/]+)+)")
"""
Regular expression to match a URL, to give a chance at guessing a reasonable
default "from" address
"""


def get_from_address(context):
    """
    Get the address that should be used for the "From" field in sent e-mails
    """
    from_addr = context.get('cs_email_from_address', None)
    if from_addr is not None:
        return from_addr
    # no address specified.
    # try to figure out a reasonable guess from cs_url_root.
    m = RE_URL.match(context.get('cs_url_root', ''))
    if m is None:
        # cs_url_root not set, or didn't match RE_URL; return None
        # (will error out later)
        return None
    return "no-reply@%s" % m.group(2)


def get_smtp_config_vars(context):
    """
    Get the values of e-mail-related configuration variables.
    """
    host = context.get('cs_smtp_host', 'localhost')
    port = context.get('cs_smtp_port', 25)
    user = context.get('cs_smtp_user', None)
    passwd = context.get('cs_smtp_password', None)
    return host, port, user, passwd


def get_smtp_object(context):
    """
    Return an smtplib.SMTP object to use for sending e-mail.
    """
    host, port, user, passwd = get_smtp_config_vars(context)
    try:
        smtp = setup_smtp_object(smtplib.SMTP(host, port), user, passwd)
        return smtp
    except:
        return None


def setup_smtp_object(smtp, user, passwd):
    """
    Set up an smtplib.SMTP object for use with CAT-SOOP, enabling TLS if
    possible and logging in a user if information is specified.
    """
    smtp.set_debuglevel(False)
    smtp.ehlo()
    if user is not None and passwd is not None:
        if smtp.has_extn('STARTTLS'):
            smtp.starttls()
            smtp.ehlo()
        smtp.login(user, passwd)
    return smtp


def can_send_email(context, smtp=-1):
    """
    Test whether CAT-SOOP can send e-mail as currently configured
    """
    if smtp == -1:
        smtp = get_smtp_object(context)
    return smtp is not None and get_from_address(context) is not None


def send_email(context, to_addr, subject, body, html_body=None):
    """
    Send an e-mail.

    to_addr: A string containing a single e-mail address for the recipient, or
             an iterable containing multiple recipient addresses.
    subject: A string representing the subject of the e-mail message
    body: A string representing the contents of the e-mail (plain text)
    html_body: A string representing the contents of the e-mail in HTML mode,
               or None to send only a plain-text message
    """
    if not isinstance(to_addr, (list, tuple, set)):
        to_addr = [to_addr]
    if not can_send_email(context):
        return dict((a, None) for a in to_addr)
    msg = MIMEText(body, 'plain')
    if html_body is not None:
        _m = msg
        msg = MIMEMultipart('alternative')
        msg.attach(_m)
        msg.attach(MIMEText(html_body, 'html'))
    msg['To'] = ', '.join(to_addr)
    msg['From'] = _from = get_from_address(context)
    msg['Subject'] = subject
    smtp = get_smtp_object(context)
    try:
        smtp.sendmail(_from, to_addr, msg.as_string())
        out = {}
        smtp.close()
    except:
        out = dict((a, None) for a in to_addr)
    return out
