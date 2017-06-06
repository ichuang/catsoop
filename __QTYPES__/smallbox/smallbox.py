# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
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

import collections.abc

defaults = {
    'csq_soln': '',
    'csq_check_function': lambda sub, soln: sub.strip() == soln.strip(),
    'csq_npoints': 1,
    'csq_msg_function': lambda sub, soln: '',
    'csq_show_check': False
}


def escape(s):
    return s.replace('"', '&quot;')


def total_points(**info):
    return info['csq_npoints']


def handle_submission(submissions, **info):
    check = info['csq_check_function']
    sub = submissions[info['csq_name']]
    soln = info['csq_soln']
    check_result = check(sub, soln)
    if isinstance(check_result, collections.abc.Mapping):
        score = check_result['score']
        msg = check_result['msg']
    elif isinstance(check_result, collections.abc.Sequence):
        score, msg = check_result
    else:
        score = check_result
        mfunc = info['csq_msg_function']
        try:
            msg = mfunc(sub, soln)
        except:
            try:
                msg = mfunc(sub)
            except:
                msg = ''
    percent = float(score)
    if info['csq_show_check']:
        if percent == 1.0:
            response = '<img src="BASE/images/check.png" />'
        elif percent == 0.0:
            response = '<img src="BASE/images/cross.png" />'
        else:
            response = ''
    else:
        response = ''
    response += msg
    return {'score': percent, 'msg': response}


def render_html(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '<input type="text"'
    if info.get('csq_size', None) is not None:
        out += ' size="%s"' % info['csq_size']

    out += ' value="%s"' % escape(last_log.get(info['csq_name'], ''))
    out += ' name="%s"' % info['csq_name']
    out += ' id="%s"' % info['csq_name']
    return out + ' />'


def answer_display(**info):
    out = "Solution: %s" % (info['csq_soln'])
    return out
