# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

defaults = {
    'csq_soln': '',
    'csq_check_function': lambda sub, soln: (sub.strip() == soln.strip()),
    'csq_npoints': 1,
    'csq_msg_function': lambda sub: (''),
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
