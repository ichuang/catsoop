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

defaults = {
    'csq_soln': '',
    'csq_check_function': lambda sub, soln: (sub.strip() == soln.strip()),
    'csq_npoints': 1,
    'csq_msg_function': lambda sub: (''),
    'csq_rows': 10,
    'csq_cols': 60,
    'csq_show_check': False
}


def escape(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace(
        '<', '&lt;').replace('>', '&gt;')


def total_points(**info):
    return info['csq_npoints']


def handle_submission(submissions, **info):
    check = info['csq_check_function']
    sub = submissions[info['csq_name']]
    soln = info['csq_soln']
    percent = float(check(sub, soln))
    if info['csq_show_check']:
        if percent == 1.0:
            msg = '<img src="BASE/images/check.png" />'
        elif percent == 0.0:
            msg = '<img src="BASE/images/cross.png" />'
        else:
            msg = ''
    else:
        msg = ''
    msg += info['csq_msg_function'](submissions[info['csq_name']])
    return {'score': percent, 'msg': msg}


def render_html(last_log, **info):
    if last_log is None:
        last_log = {}
    rows = info['csq_rows']
    cols = info['csq_cols']
    out = '<textarea rows="%d" cols="%d"' % (rows, cols)
    out += ' name="%s"' % info['csq_name']
    out += ' id="%s"' % info['csq_name']
    out += '>%s</textarea><br>' % escape(last_log.get(info['csq_name'], ''))
    return out


def answer_display(**info):
    out = "<p>Solution: %s<p>" % (info['csq_soln'])
    return out
