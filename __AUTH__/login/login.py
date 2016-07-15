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

import os
import re
import random
import string
import hashlib

from operator import xor
from struct import Struct
from itertools import starmap


def get_logged_in_user(context):
    # form-based login
    base_context = context['csm_base_context']
    logging = context['csm_logging'].get_logger(context)
    loader = context['csm_loader']
    form = context.get('cs_form', {})
    mail = context['csm_mail']

    session = context['cs_session_data']
    action = form.get('loginaction', '')
    message = form.get('message', '')

    hash_iterations = context.get('cs_password_hash_iterations', 250000)
    url = _get_base_url(context)

    # if the user is trying to log out, do that.
    if action == 'logout':
        context['cs_session_data'] = {}
        return {'cs_reload': True}

    # if a user is changing their password
    elif action == 'change_password':
        uname = session.get('username', None)
        if uname is None:
            # cannot change password without first being logged in
            base = _get_base_url(context)
            context['cs_content_header'] = "Please Log In"
            context['cs_content'] = ("You cannot change your password "
                                     "until you have logged in.<br/>"
                                     '<a href="%s">Go Back</a>') % base
            context['cs_handler'] = 'passthrough'
            return {'cs_render_now': True}
        login_info = logging.most_recent(None, uname, 'logininfo', {})
        if not login_info.get('confirmed', False):
            # show the confirmation message again
            context['cs_content_header'] = "Your E-mail Has Not Been Confirmed"
            context['cs_content'] = ("Your registration is not yet "
                                     "complete.  Please check your"
                                     " e-mail for instructions on "
                                     "how to complete the process.  "
                                     "If you did not receive a "
                                     "confirmation e-mail, please "
                                     "<a href='%s?loginaction=reconfirm_reg"
                                     "&username=%s'>click here</a> to "
                                     "re-send the email.") % (url, uname)
            context['cs_handler'] = 'passthrough'
            return {'cs_render_now': True}
        if 'oldpasswd' in form:
            # the user has submitted the form.  check it.
            errors = []
            if not check_password(context, form['oldpasswd'], uname, hash_iterations):
                errors.append('Incorrect password entered.')
            passwd = form['passwd']
            passwd2 = form['passwd2']
            if passwd != passwd2:
                errors.append('New passwords do not match.')
            else:
                p_check_result = _validate_password(context, passwd)
                if p_check_result is not None:
                    errors.append(p_check_result)
            if len(errors) > 0:
                # at least one error happened; display error message and show
                # the form again
                errs = '\n'.join('<li>%s</li>' % i for i in errors)
                lmsg = ('<font color="red">Your password was not changed:\n'
                        '<ul>%s</ul></font>') % errs
                session['login_message'] = lmsg
            else:
                # clear login info from session.
                clear_session_vars(context, 'login_message')
                # store new password.
                salt = get_new_password_salt()
                phash = compute_password_hash(passwd, salt, hash_iterations)
                login_info['password_salt'] = salt
                login_info['password_hash'] = phash
                logging.update_log(None, uname, 'logininfo', login_info)
                context['cs_content_header'] = "Password Changed!"
                base = _get_base_url(context)
                context['cs_content'] = ("Your password has been successfully"
                                         " changed.<br/>"
                                         '<a href="%s">Continue</a>') % base
                context['cs_handler'] = 'passthrough'
                return {'cs_render_now': True}

        # show the form.
        context['cs_content_header'] = 'Change Password'
        context['cs_content'] = generate_password_change_form(context)
        context['cs_handler'] = 'passthrough'
        return {'cs_render_now': True}

    # if a user is confirming their account
    elif action == 'confirm_reg':
        u = form.get('username', None)
        t = form.get('token', None)
        stored_token = logging.most_recent(None, u, 'confirmation_token', '')
        login_info = logging.most_recent(None, u, 'logininfo', {})
        context['cs_handler'] = 'passthrough'
        retval = {'cs_render_now': True}
        url = _get_base_url(context)
        if login_info.get('confirmed', False):
            context['cs_content_header'] = "Already Confirmed"
            context['cs_content'] = ("This account has already been confirmed."
                                     "  Please <a href='%s'>click here</a> to "
                                     "log in.") % url
        elif t == stored_token and 'confirmed' in login_info:
            login_info['confirmed'] = True
            logging.update_log(None, u, 'logininfo', login_info)
            context['cs_content_header'] = "Account Confirmation Succeeded"
            context['cs_content'] = ('Please <a href="%s">click here</a>'
                                     ' to log in.') % url
            clear_session_vars(context, 'login_message', 'last_form')
            retval.update(login_info)
            session.update(login_info)
            session['username'] = u
        else:
            cs_debug(t, stored_token, login_info)
            context['cs_content_header'] = "Account Confirmation Failed"
            context['cs_content'] = ("Please double-check the details "
                                     "from the confirmation e-mail you"
                                     " received.")
        return retval

    # if the session tells us someone is logged in, return their
    # information
    elif 'username' in session:
        uname = session['username']
        clear_session_vars(context, 'login_message', 'last_form')
        return {'username': uname,
                'name': session.get('name', uname),
                'email': session.get('email', uname)}

    # if a user has forgotten their password
    elif action == 'forgot_password':
        if not mail.can_send_email(context):
            # can't send e-mail; show error message
            context['cs_content_header'] = "Password Reset: Error"
            context['cs_content'] = ("This feature is not available "
                                     "on this CAT-SOOP instance.")
            context['cs_handler'] = 'passthrough'
            return {'cs_render_now': True}
        if 'uname' in form:
            # user has submitted the form; check and send request
            uname = form['uname']
            email = form.get('email', None)
            login_info = logging.most_recent(None, uname, 'logininfo', {})
            if email != login_info.get('email', ''):
                lmsg = ('<font color="red">The information you provided '
                        'does not match any known accounts.</font>')
                session['login_message'] = lmsg
                session['last_form'] = form
            else:
                # clear login info from session
                clear_session_vars(context, 'login_message', 'last_form')
                # generate and store token
                token = generate_confirmation_token()
                logging.update_log(None, uname, 'password_reset_token', token)
                # generate and send e-mail
                mail.send_email(context, email,
                                "CAT-SOOP: Confirm Password Reset",
                                *passwd_confirm_emails(context, uname, token))
                # show confirmation message
                context['cs_content_header'] = "Password Reset: Confirm"
                context['cs_content'] = ("Please check your e-mail for "
                                         "instructions on how to complete "
                                         "the process.")
                context['cs_handler'] = 'passthrough'
                return {'cs_render_now': True}

        # show the form.
        context['cs_content_header'] = 'Forgot Password'
        context['cs_content'] = ("Please enter your information below to "
                                 "reset your password.")
        context['cs_content'] += generate_forgot_password_form(context)
        context['cs_handler'] = 'passthrough'
        return {'cs_render_now': True}

    # if a user is requesting a password reset
    elif action == 'reset_password':
        if not mail.can_send_email(context):
            # can't send e-mail; show error message
            context['cs_content_header'] = "Password Reset: Error"
            context['cs_content'] = ("This feature is not available "
                                     "on this CAT-SOOP instance.")
            context['cs_handler'] = 'passthrough'
            return {'cs_render_now': True}
        if 'passwd' in form:
            # user has submitted the form; check and update password
            errors = []
            u = form.get('username', None)
            t = form.get('token', None)
            stored_token = logging.most_recent(None, u, 'password_reset_token',
                                             '')
            if stored_token != t:
                errors.append('Unknown user, or incorrect confirmation token.')
            passwd = form['passwd']
            passwd2 = form['passwd2']
            if passwd != passwd2:
                errors.append('New passwords do not match.')
            else:
                p_check_result = _validate_password(context, passwd)
                if p_check_result is not None:
                    errors.append(p_check_result)
            if len(errors) > 0:
                # at least one error happened; display error message and show
                # the form again
                errs = '\n'.join('<li>%s</li>' % i for i in errors)
                lmsg = ('<font color="red">Your password was not reset:\n'
                        '<ul>%s</ul></font>') % errs
                session['login_message'] = lmsg
            else:
                # success!
                # clear login info from session.
                clear_session_vars(context, 'login_message')
                # store new password.
                login_info = logging.most_recent(None, u, 'logininfo', {})
                salt = get_new_password_salt()
                phash = compute_password_hash(passwd, salt, hash_iterations)
                login_info['password_salt'] = salt
                login_info['password_hash'] = phash
                logging.update_log(None, u, 'logininfo', login_info)
                context['cs_content_header'] = "Password Changed!"
                base = _get_base_url(context)
                context['cs_content'] = ("Your password has been successfully"
                                         " changed.<br/>"
                                         '<a href="%s">Continue</a>') % base
                context['cs_handler'] = 'passthrough'
                email = login_info.get('email', u)
                name = login_info.get('name', u)
                info = {'username': u, 'name': name, 'email': email}
                session.update(info)
                return {'cs_render_now': True}
        # show the form.
        context['cs_content_header'] = 'Reset Password'
        context['cs_content'] = generate_password_reset_form(context)
        context['cs_handler'] = 'passthrough'
        return {'cs_render_now': True}

    # if the form has login information, we should try to authenticate
    elif action == 'login':
        uname = form.get('login_uname', '')
        if uname == '':
            clear_session_vars(context, 'login_message')

        entered_password = form.get('login_passwd', '')

        valid_uname = True
        if _validate_email(context, uname) is None:
            # this looks like an e-mail address, not a username.
            # find the associated username, if any
            # TODO: implement caching of some kind so this isn't so slow/involved
            data_root = context.get('cs_data_root', base_context.cs_data_root)
            global_log_dir = os.path.join(data_root, '__LOGS__')
            for d in os.listdir(global_log_dir):
                if not d.endswith('.db'):
                    continue
                u = d[:-3]
                e = logging.most_recent(None, u, 'logininfo', {})
                e = e.get('email', None)
                if e == uname:
                    uname = u
                    break

        vmsg = _validate_username(context, uname)
        if vmsg is not None:
            valid_uname = False
            lmsg = ('<font color="red">' + vmsg + '</font>')
            session.update({'login_message': lmsg, 'last_form': form})
        valid_pwd = check_password(context, entered_password, uname, hash_iterations)
        if valid_uname and valid_pwd:
            # successful login
            login_info = logging.most_recent(None, uname, 'logininfo', {})
            if not login_info.get('confirmed', False):
                # show the confirmation message again
                context[
                    'cs_content_header'] = "Your E-mail Has Not Been Confirmed"
                context['cs_content'] = ("Your registration is not yet "
                                         "complete.  Please check your"
                                         " e-mail for instructions on "
                                         "how to complete the process.  "
                                         "If you did not receive a "
                                         "confirmation e-mail, please "
                                         "<a href='%s?loginaction=reconfirm_reg"
                                         "&username=%s'>click here</a> to "
                                         "re-send the email.") % (url, uname)
                context['cs_handler'] = 'passthrough'
                return {'cs_render_now': True}
            email = login_info.get('email', uname)
            name = login_info.get('name', uname)
            info = {'username': uname, 'name': name, 'email': email}
            session.update(info)
            clear_session_vars(context, 'login_message')
            info['cs_reload'] = True
            return info
        elif valid_uname:
            lmsg = ('<font color="red">'
                    'Incorrect username or password.'
                    '</font>')
            session.update({'login_message': lmsg, 'last_form': form})

    # a user is asking to re-send the confirmation message
    elif action == 'reconfirm_reg':
        uname = form.get('username', None)
        token = logging.most_recent(None, uname, 'confirmation_token', None)
        login_info = logging.most_recent(None, uname, 'logininfo')
        if login_info.get('confirmed', False):
            context['cs_content_header'] = "Already Confirmed"
            context['cs_content'] = ("This account has already been confirmed."
                                     "  Please <a href='%s'>click here</a> to "
                                     "log in.") % url
        elif token is None:
            context['cs_content_header'] = "Error"
            context['cs_content'] = ("The provided information is "
                                     "complete.  Please check your"
                                     " e-mail for instructions on "
                                     "how to complete the process.")
        else:
            # generate and send e-mail
            mail.send_email(context, login_info['email'],
                            "CAT-SOOP: Confirm E-mail Address",
                            *reg_confirm_emails(context, uname, token))
            context['cs_content_header'] = "Confirmation E-mail Sent"
            context['cs_content'] = ("Your registration is almost "
                                     "complete.  Please check your"
                                     " e-mail for instructions on "
                                     "how to complete the process.  "
                                     "If you do not receive a "
                                     "confirmation e-mail within 5 minutes, please "
                                     "<a href='%s?loginaction=reconfirm_reg"
                                     "&username=%s'>click here</a> to "
                                     "re-send the email.") % (url, uname)
        context['cs_handler'] = 'passthrough'
        return {'cs_render_now': True}

    # if we are looking at a registration action
    elif action == 'register':
        if not context.get('cs_allow_registration', True):
            return {'cs_render_now': True}
        uname = form.get('uname', '').strip()
        if uname != '':
            # form has been filled out.  validate (mirrors javascript checks).
            email = form.get('email', '').strip()
            email2 = form.get('email2', '').strip()
            passwd = form.get('passwd', '')
            passwd2 = form.get('passwd2', '')
            name = form.get('name', '').strip()
            if name == '':
                name = uname
            errors = []
            # validate e-mail
            if len(email) == 0:
                errors.append("No e-mail address entered.")
            elif email != email2:
                errors.append("E-mail addresses do not match.")
            else:
                e_check_result = _validate_email(context, email)
                if e_check_result is not None:
                    errors.append(e_check_result)
            # validate username
            uname_okay = True
            if len(uname) == 0:
                errors.append("No username entered.")
                uname_okay = False
            else:
                u_check_result = _validate_username(context, uname)
                if u_check_result is not None:
                    errors.append(u_check_result)
                    uname_okay = False
            if uname_okay:
                login_info = logging.most_recent(None,
                                               uname,
                                               'logininfo',
                                               default=None)
                if uname.lower() == 'none' or login_info is not None:
                    errors.append('Username %s is not available.' % uname)
            # validate password
            if passwd != passwd2:
                errors.append('Passwords do not match.')
            else:
                p_check_result = _validate_password(context, passwd)
                if p_check_result is not None:
                    errors.append(p_check_result)

            if len(errors) > 0:
                # at least one error happened; display error message and show
                # registration form again
                errs = '\n'.join('<li>%s</li>' % i for i in errors)
                lmsg = ('<font color="red">Your account was not created:\n'
                        '<ul>%s</ul></font>') % errs
                session['login_message'] = lmsg
                session['last_form'] = form
            else:
                # clear login info from session
                clear_session_vars(context, 'login_message', 'last_form')
                # generate new salt and password hash
                salt = get_new_password_salt()
                phash = compute_password_hash(passwd, salt, hash_iterations)
                # if necessary, send confirmation e-mail
                # otherwise, treat like already confirmed
                if (mail.can_send_email(context) and
                        context.get('cs_require_confirm_email', True)):
                    # generate and store token
                    token = generate_confirmation_token()
                    logging.overwrite_log(None, uname, 'confirmation_token',
                                        token)
                    # generate and send e-mail
                    mail.send_email(context, email,
                                    "CAT-SOOP: Confirm E-mail Address",
                                    *reg_confirm_emails(context, uname, token))
                    confirmed = False
                else:
                    confirmed = True
                # store login information
                uinfo = {'password_salt': salt,
                         'password_hash': phash,
                         'email': email,
                         'name': name,
                         'confirmed': confirmed}
                logging.overwrite_log(None, uname, 'logininfo', uinfo)
                if confirmed:
                    # load user info into session
                    info = {'username': uname, 'name': name, 'email': email}
                    session.update(info)
                    # redirect to current location, with no "logininfo" in URL
                    info['cs_reload'] = True
                    return info
                else:
                    # show a "please confirm" message
                    context['cs_content_header'] = "Thank You!"
                    context['cs_content'] = ("Your registration is almost "
                                             "complete.  Please check your"
                                             " e-mail for instructions on "
                                             "how to complete the process.  "
                                             "If you do not receive a "
                                             "confirmation e-mail within 5 minutes, please "
                                             "<a href='%s?loginaction=reconfirm_reg"
                                             "&username=%s'>click here</a> to "
                                             "re-send the email.") % (url, uname)
                    context['cs_handler'] = 'passthrough'
                    return {'cs_render_now': True}

        # if we haven't returned something else by now, show the
        # registration form
        context['cs_content_header'] = 'Register'
        context['cs_content'] = generate_registration_form(context)
        context['cs_handler'] = 'passthrough'
        return {'cs_render_now': True}

    if action != 'login':
        clear_session_vars(context, 'login_message')

    # no one is logged in; show the login form.
    context['cs_content_header'] = 'Please Log In To Continue'
    context['cs_content'] = generate_login_form(context)
    context['cs_handler'] = 'passthrough'
    return {'cs_render_now': True}


def clear_session_vars(context, *args):
    """
    Helper function to clear session variables
    """
    session = context['cs_session_data']
    for i in args:
        try:
            del session[i]
        except:
            pass


def check_password(context, provided, uname, iterations=250000):
    """
    Compare the provided password against a stored hash.
    """
    logging = context['csm_logging'].get_logger(context)
    user_login_info = logging.most_recent(None, uname, 'logininfo', {})
    pass_hash = user_login_info.get('password_hash', None)
    if pass_hash is not None:
        salt = user_login_info.get('password_salt', None)
        hashed_pass = compute_password_hash(provided, salt, iterations)
        if hashed_pass == pass_hash:
            return True
    return False


def get_new_password_salt(length=128):
    """
    Generate a new salt of length length.  Tries to use os.urandom, and
    falls back on random if that doesn't work for some reason.
    """
    try:
        return os.urandom(length)
    except:
        return ''.join(chr(random.randint(0, 255)) for i in range(length))


def _ensure_bytes(x):
    try:
        return x.encode()
    except:
        return x


def compute_password_hash(password, salt=None, iterations=250000):
    """
    Given a password, and (optionally) an associated salt, return a hash value.
    """
    return hashlib.pbkdf2_hmac('sha512', _ensure_bytes(password),
                               _ensure_bytes(salt), iterations)


def generate_confirmation_token(n=20):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for i in range(n))


def _get_base_url(context):
    return '/'.join([context['cs_url_root']] + context['cs_path_info'])


def generate_forgot_password_form(context):
    """
    Generate a "forgot password" form.
    """
    base = _get_base_url(context)
    req_url = base + '?loginaction=forgot_password'
    out = '<form method="POST" action="%s">' % req_url
    msg = context['cs_session_data'].get('login_message', None)
    if msg is not None:
        out += '\n%s<p>' % msg
    last = context['cs_session_data'].get('last_form', {})
    last_uname = last.get('uname', '').replace('"', '&quot;')
    last_email = last.get('email', '').replace('"', '&quot;')
    out += ('\n<table>'
            '\n<tr>'
            '\n<td style="text-align:right;">Username:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="uname" '
            'id="uname" '
            'value="%s"/>'
            '\n</td>'
            '\n</tr>') % last_uname
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Email Address:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="email" '
            'id="email" '
            'value="%s" />'
            '\n</td>'
            '\n</tr>') % last_email
    out += ('\n<tr>'
            '\n<td style="text-align:right;"></td>'
            '\n<td style="text-align:right;">'
            '\n<input type="submit" value="Reset Password"></td>'
            '\n</tr>')
    out += '\n</table>\n</form>'
    return out


def generate_password_reset_form(context):
    """
    Generate a "reset password" form.
    """
    base = _get_base_url(context)
    req_url = base + '?loginaction=reset_password'
    req_url += '&username=%s' % context['cs_form']['username']
    req_url += '&token=%s' % context['cs_form']['token']
    out = '<form method="POST" action="%s" id="pwdform">' % req_url
    msg = context['cs_session_data'].get('login_message', None)
    if msg is not None:
        out += '\n%s<p>' % msg
    safe_uname = context['cs_form']['username'].replace('"', '&quot;')
    out += '\n<input type="hidden" name="uname" id="uname" value="%s" />' % safe_uname
    out += '\n<table>'
    out += ('\n<tr>'
            '\n<td style="text-align:right;">New Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd" id="passwd" />'
            '\n</td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Confirm New Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd2" id="passwd2" />'
            '\n</td>'
            '\n<td><span id="pwd_check"></span></td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;"></td>'
            '\n<td style="text-align:right;">')
    out += _submit_button(['passwd', 'passwd2'],
                          'uname',
                          'pwdform', 'Change Password')
    out += '</td>\n</tr>'
    out += '\n</table>\n</form>'
    out += CHANGE_PASSWORD_FORM_CHECKER
    return out


def generate_password_change_form(context):
    """
    Generate a "change password" form.
    """
    base = _get_base_url(context)
    req_url = base + '?loginaction=change_password'
    out = '<form method="POST" action="%s" id="pwdform">' % req_url
    msg = context['cs_session_data'].get('login_message', None)
    if msg is not None:
        out += '\n%s<p>' % msg
    safe_uname = context['cs_session_data']['username'].replace('"', '&quot;')
    out += '\n<input type="hidden" name="uname" id="uname" value="%s" />' % safe_uname
    out += '\n<table>'
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Current Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="oldpasswd" id="oldpasswd" />'
            '\n</td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;">New Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd" id="passwd" />'
            '\n</td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Confirm New Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd2" id="passwd2" />'
            '\n</td>'
            '\n<td><span id="pwd_check"></span></td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;"></td>'
            '\n<td style="text-align:right;">')
    out += _submit_button(['passwd', 'passwd2', 'oldpasswd'],
                          'uname',
                          'pwdform', 'Change Password')
    out += '</td>\n</tr>'
    out += '\n</table>\n</form>'
    out += CHANGE_PASSWORD_FORM_CHECKER
    return out


def generate_login_form(context):
    """
    Generate a login form.
    """
    base = _get_base_url(context)
    out = '<form method="POST" id="loginform" action="%s">' % (base + '?loginaction=login')
    msg = context['cs_session_data'].get('login_message', None)
    last_uname = context['cs_session_data'].get('last_form', {}).get(
        'login_uname', '')
    if msg is not None:
        out += '\n%s<p>' % msg
    last_uname = last_uname.replace('"', '&quot;')
    out += ('\n<table>'
            '\n<tr>'
            '\n<td style="text-align:right;">Username:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="login_uname" '
            'id="login_uname" '
            'value="%s"/>'
            '\n</td>'
            '\n</tr>'
            '\n<tr>'
            '\n<td style="text-align:right;">Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" '
            'name="login_passwd" '
            'id="login_passwd" />'
            '\n</td>'
            '\n</tr>'
            '\n<tr>'
            '\n<td style="text-align:right;"></td>'
            '\n<td style="text-align:right;">') % last_uname
    out += _submit_button(['login_passwd'],
                          'login_uname',
                          'loginform', 'Log In')
    out += ('<td>\n</tr>'
            '\n</table>')
    out += '<p>'
    if mail.can_send_email(context):
        base = _get_base_url(context)
        loc = base + '?loginaction=forgot_password'
        out += ('\nForgot your password?  '
                'Click <a href="%s">here</a>.<br/>') % loc
    if context.get('cs_allow_registration', True):
        loc = _get_base_url(context)
        loc += '?loginaction=register'
        link = '<a href="%s">create one</a>' % loc
        out += '\nIf you do not already have an account, please %s.' % link
    out += '</p>'
    return out + '</form>'


def generate_registration_form(context):
    """
    Generate a registration form.
    """
    base = _get_base_url(context)
    qstring = '?loginaction=register'
    out = '<form method="POST" action="%s" id="regform">' % (base + qstring)
    last = context['cs_session_data'].get('last_form', {})
    msg = context['cs_session_data'].get('login_message', None)
    if msg is not None:
        out += '\n%s<p>' % msg
    last_name = last.get('name', '').replace('"', '&quot;')
    last_uname = last.get('uname', '').replace('"', '&quot;')
    last_email = last.get('email', '').replace('"', '&quot;')
    last_email2 = last.get('email2', '').replace('"', '&quot;')
    out += ('\n<table>'
            '\n<tr>'
            '\n<td style="text-align:right;">Username:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="uname" '
            'id="uname" '
            'value="%s"/>'
            '\n</td>'
            '\n<td><span id="uname_check"></span></td>'
            '\n</tr>') % last_uname
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Email Address:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="email" '
            'id="email" '
            'value="%s" />'
            '\n</td>'
            '\n</tr>') % last_email
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Confirm Email Address:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" '
            'name="email2" '
            'id="email2" '
            'value="%s"/>'
            '\n</td>'
            '\n<td><span id="email_check"></span></td>'
            '\n</tr>') % last_email2
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd" id="passwd" />'
            '\n</td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Confirm Password:</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="password" name="passwd2" id="passwd2" />'
            '\n</td>'
            '\n<td><span id="pwd_check"></span></td>'
            '\n</tr>')
    out += ('\n<tr>'
            '\n<td style="text-align:right;">Name (Optional):</td>'
            '\n<td style="text-align:right;">'
            '\n<input type="text" name="name" id="name" value="%s"/>'
            '\n</td>'
            '\n</tr>') % last_name
    out += ('\n<tr>'
            '\n<td style="text-align:right;"></td>'
            '\n<td style="text-align:right;">')
    out += _submit_button(['passwd', 'passwd2'],
                          'uname',
                          'regform', 'Register')
    out += ('\n</td>'
            '\n</tr>')
    out += REGISTRATION_FORM_CHECKER
    return out + '</table></form>'


def _run_validators(validators, x):
    for extra_validator_regexp, error_msg in validators:
        if not re.match(extra_validator_regexp, x):
            return error_msg
    return None

# PASSWORD VALIDATION

_pwd_too_short_msg = "Passwords must be at least 5 characters long."

_validate_password_javascript = r"""
function _validate_password(p){
    if (p.length < 5){
        return %r;
    }
    return null;
}
""" % (_pwd_too_short_msg)


def _validate_password(context, p):
    if len(p) < 5:
        return _pwd_too_short_msg
    return _run_validators(context.get('cs_extra_password_validators', []), p)

# EMAIL VALIDATION

# email validation regex from http://www.regular-expressions.info/email.html
_re_valid_email_string = r"^[A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9-]{1,63}\.){1,125}[A-Za-z]{2,63}$"
RE_VALID_EMAIL = re.compile(_re_valid_email_string)

_eml_too_long_msg = "E-mail addresses must be less than 255 characters long."
_eml_invalid_msg = "Please make sure you have entered a valid e-mail address."

_validate_email_javascript = r"""
var _re_valid_email = /%s/;
function _validate_email(e){
    if (e.length > 254) {
        return %r;
    } else if (!_re_valid_email.test(e)){
        return %r;
    }
    return null;
}
""" % (_re_valid_email_string, _eml_too_long_msg, _eml_invalid_msg)


def _validate_email(context, e):
    if len(e) > 254:
        return _eml_too_long_msg
    elif not RE_VALID_EMAIL.match(e):
        return _eml_invalid_msg
    return _run_validators(context.get('cs_extra_email_validators', []), e)

# USERNAME VALIDATION

_re_valid_username_string = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
RE_VALID_USERNAME = re.compile(_re_valid_username_string)

_uname_too_short_msg = "Usernames must contain at least one character."
_uname_wrong_start_msg = "Usernames must begin with an ASCII letter or number."
_uname_invalid_msg = ("Usernames must contain only letters and numbers, "
                      "dashes (-), underscores (_), and periods (.).")

_validate_username_javascript = r"""
var _re_valid_uname = /%s/;
function _validate_username(u){
    if (u.length < 1){
        return %r;
    } else if (!_re_valid_uname.test(u)){
        if (!_re_valid_uname.test(u.charAt(0))){
            return %r;
        }else{
            return %r;
        }
    }
    return null;
}
""" % (_re_valid_username_string, _uname_too_short_msg, _uname_wrong_start_msg,
       _uname_invalid_msg)


def _validate_username(context, u):
    if len(u) < 1:
        return _uname_too_short_msg
    elif not RE_VALID_USERNAME.match(u):
        if not RE_VALID_USERNAME.match(u[0]):
            return _uname_wrong_start_msg
        else:
            return _uname_invalid_msg
    return _run_validators(context.get('cs_extra_username_validators', []), u)


REGISTRATION_FORM_CHECKER = """<script type="text/javascript">
%s
%s
%s
function check_form(){
    var e_msg = "";
    var u_msg = "";
    var p_msg = "";

    // validate email
    var e_val = $("#email").val();
    if(e_val.length == 0){
        e_msg = "Please enter an email address.";
    }else if(e_val != $("#email2").val()){
        e_msg = "E-mail addresses do not match.";
    }else{
        var e_check_result = _validate_email(e_val);
        if (e_check_result !== null){
            e_msg = e_check_result;
        }
    }
    $("#email_check").html('<font color="red">' + e_msg + '</font>');

    // validate username
    var u_val = $("#uname").val();
    if(u_val.length == 0){
        u_msg = "Please enter a username.";
    }else{
        var u_check_result = _validate_username(u_val);
        if (u_check_result !== null){
            u_msg = u_check_result;
        }
    }
    $("#uname_check").html('<font color="red">' + u_msg + '</font>');

    // validate password
    var p_val = $("#passwd").val();
    if(p_val != $("#passwd2").val()){
        p_msg = "Passwords do not match.";
    }else{
        var p_check_result = _validate_password(p_val);
        if (p_check_result !== null){
            p_msg = p_check_result;
        }
    }
    $("#pwd_check").html('<font color="red">' + p_msg + '</font>');
}
$(document).ready(check_form);
$("#regform").keyup(check_form);
</script>""" % (_validate_email_javascript, _validate_username_javascript,
                _validate_password_javascript)
"Javascript code for checking inputs to the registration form"

CHANGE_PASSWORD_FORM_CHECKER = """<script type="text/javascript">
%s
function check_form(){
    var p_msg = "";

    // validate password
    var p_val = $("#passwd").val();
    if(p_val != $("#passwd2").val()){
        p_msg = "Passwords do not match.";
    }else{
        var p_check_result = _validate_password(p_val);
        if (p_check_result !== null){
            p_msg = p_check_result;
        }
    }
    $("#pwd_check").html('<font color="red">' + p_msg + '</font>');
}
$(document).ready(check_form);
$("#pwdform").keyup(check_form);
</script>""" % _validate_password_javascript
"Javascript code for checking inputs to the password change form"


def reg_confirm_emails(context, username, confirmation_code):
    """
    @param context: The context associated with this request
    @param username: The username of the user who needs to confirm
    @param confirmation_code: The user's confirmation token (from
    L{generate_confirmation_token})
    @return: A 2-tuple representing the message to be sent.  The first element
    is the plain-text version of the e-mail, and the second is the HTML
    version.
    """
    base = _get_base_url(context)
    u = "%s?loginaction=confirm_reg&username=%s&token=%s" % (base, username,
                                                             confirmation_code)
    url_root = context['cs_url_root']
    return (_reg_confirm_msg_base_plain % (username, url_root, u),
            _reg_confirm_msg_base_html % (username, url_root, u, u))


_reg_confirm_msg_base_plain = r"""You recently signed up for an account with username %s at the CAT-SOOP instance at %s.

In order to confirm your account, please visit the following URL:
%s

If you did not sign up for this account, or if you otherwise feel that you
are receiving this message in error, please ignore or delete it."""

_reg_confirm_msg_base_html = r"""<p>You recently signed up for an account with username <tt>%s</tt> at the CAT-SOOP instance at <tt>%s</tt>.</p>

<p>In order to confirm your account, please click on the following link:<br/>
<a href="%s">%s</a></p>

<p>If you did not sign up for this account, or if you otherwise feel that you
are receiving this message in error, please ignore or delete it.</p>"""


def passwd_confirm_emails(context, username, code):
    """
    @param context: The context associated with this request
    @param username: The username of the user who needs to confirm
    @param confirmation: The user's confirmation token (from
    L{generate_confirmation_token})
    @return: A 2-tuple representing the message to be sent.  The first element
    is the plain-text version of the e-mail, and the second is the HTML
    version.
    """
    base = _get_base_url(context)
    u = "%s?loginaction=reset_password&username=%s&token=%s" % (base, username,
                                                                code)
    url_root = context['cs_url_root']
    return (_passwd_confirm_msg_base_plain % (username, url_root, u),
            _passwd_confirm_msg_base_html % (username, url_root, u, u))


_passwd_confirm_msg_base_plain = r"""You recently submitted a request to reset the password for an account with username %s at the CAT-SOOP instance at %s.

In order to reset your password, please visit the following URL:
%s

If you did not submit this request, or if you otherwise feel that you
are receiving this message in error, please ignore or delete it."""

_passwd_confirm_msg_base_html = r"""<p>You recently submitted a request to reset the password for an account with username <tt>%s</tt> at the CAT-SOOP instance at <tt>%s</tt>.</p>

<p>In order to reset your password, please click on the following link:<br/>
<a href="%s">%s</a></p>

<p>If you did not submit this request, or if you otherwise feel that you
are receiving this message in error, please ignore or delete it.</p>"""


def _submit_button(fields, username, form, value='Submit'):
    return ('<input type="button"'
            ' value="%s"'
            ' onclick="hashlib.hash_passwords(%r, %r, %r)" />') % (value,
                                                                   fields,
                                                                   username,
                                                                   form)
