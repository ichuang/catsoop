# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import ast
import collections.abc
import traceback

tutor.qtype_inherit('smallbox')
base1, _ = tutor.question('pythoncode')

defaults.update({
    'csq_soln': '',
    'csq_check_function': lambda sub, soln: ((type(sub) == type(soln)) and
                                             (sub == soln)),
    'csq_input_check': lambda sub: None,
    'csq_npoints': 1,
    'csq_msg_function': lambda sub, soln: '',
    'csq_show_check': False,
    'csq_code_pre': '',
    'csq_mode': 'raw',
    'csq_size': 50
})

def gensym(code=''):
    pre = n = '___'
    count = 0
    while n in code:
        n = '%s%s' % (pre, count)
        count += 1
    return n

def handle_submission(submissions, **info):
    py3k = info.get('csq_python3', True)
    sub = submissions[info['csq_name']]

    inp = info['csq_input_check'](sub)
    if inp is not None:
        return {'score': 0.0, 'msg': '<font color="red">%s</font>' % inp}

    base1['get_sandbox'](info)
    if info['csq_mode'] == 'raw':
        soln = info['csq_soln']
    else:
        code = info['csq_code_pre']
        s = info['csq_soln']
        varname = gensym(code + s)
        code += '\n%s = %s' % (varname, s)
        if py3k:
            code += '\nprint(repr(%s))' % varname
        else:
            code += '\nprint repr(%s)' % varname
        opts = info.get('csq_options', {})
        soln = eval(info['sandbox_run_code'](info, code, opts)[1], info)
    try:
        code = info['csq_code_pre']
        if sub == '':
            return {'score': 0.0, 'msg': ''}
        varname = gensym(code + sub)
        code += '\n%s = %s' % (varname, sub)
        if py3k:
            code += '\nprint(repr(%s))' % varname
        else:
            code += '\nprint repr(%s)' % varname
        opts = info.get('csq_options', {})
        fname, out, err = info['sandbox_run_code'](info, code, opts)
        sub = eval(out, info)
    except:
        msg = ''
        mfunc = info['csq_msg_function']
        try:
            msg += mfunc(sub, soln)
        except:
            try:
                msg += mfunc(sub)
            except:
                pass
        return {'score': 0.0,
                'msg': msg}

    check = info['csq_check_function']
    try:
        check_result = check(sub, soln)
    except:
        err = info['csm_errors']
        e = err.html_format(err.clear_info(info, traceback.format_exc()))
        check_result = (0.0, '<font color="red">An error occurred in the checker: <pre>%s</pre></font>' % e)

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
    response = ''
    if info['csq_show_check']:
        if percent == 1.0:
            response = '<img src="BASE/images/check.png" />'
        elif percent == 0.0:
            response = '<img src="BASE/images/cross.png" />'

    response += msg

    return {'score': percent, 'msg': response}


def answer_display(**info):
    if info['csq_mode'] == 'raw':
        out = "<p>Solution: <tt>%r</tt><p>" % (info['csq_soln'], )
    else:
        out = "<p>Solution: <tt>%s</tt><p>" % (info['csq_soln'], )
    return out
