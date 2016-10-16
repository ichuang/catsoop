# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json
import collections.abc

def default_checkbox_checker(x, y):
    return float(len([i for i, j in zip(x, y) if i == j])) / len(y)

defaults = {
    'csq_soln': '--',
    'csq_npoints': 1,
    'csq_check_function': lambda x, y: (x == y) * 1.0,
    'csq_checkbox_check_function': default_checkbox_checker,
    'csq_msg_function': lambda sub: '',
    'csq_options': [],
    'csq_show_check': False,
    'csq_multiplechoice_renderer': 'dropdown',
    'csq_multiplechoice_soln_mode': 'value',
}


def total_points(**info):
    return info['csq_npoints']


def handle_submission(submissions, **info):
    check = info['csq_check_function']
    soln = info['csq_soln']
    sub = submissions[info['csq_name']]
    if info['csq_multiplechoice_renderer'] == 'checkbox':
        try:
            sub = json.loads(sub)
        except:
            sub = {}
        _sub = []
        for ix in range(len(info['csq_options'])):
            n = "%s_opt%d" % (info['csq_name'], ix)
            _sub.append(sub.get(n, False))
        sub = _sub
        if check is defaults['csq_check_function']:
            check = defaults['csq_checkbox_check_function']
    else:
        sub = int(sub)
        if info['csq_multiplechoice_soln_mode'] == 'value':
            sub = info['csq_options'][sub]
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
    r = info['csq_multiplechoice_renderer']
    if r in _renderers:
        return _renderers[r](last_log, **info)
    else:
        return ("<font color='red'>"
                "Invalid <tt>multiplechoice</tt> renderer: %s"
                "</font>") % r


def render_html_dropdown(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '\n<select name="%s" >' % info['csq_name']
    for (ix, i) in enumerate(['--'] + info['csq_options']):
        out += '\n<option value="%s" ' % (ix - 1)
        if last_log.get(info['csq_name'], '-1') == str(ix - 1):
            out += "selected "
        out += '>%s</option>' % i
    out += '</select>'
    return out


def render_html_checkbox(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '<table border="0">'
    name = info['csq_name']
    last = last_log.get(info['csq_name'], None)
    if last is None:
        last = {}
    else:
        try:
            last = json.loads(last)
        except:
            last = {}
        if not isinstance(last, dict):
            try:
                last = {("%s_opt%d" % (name, last)): True}
            except:
                last = {}
    checked = set()
    for (ix, i) in enumerate(info['csq_options']):
        out += '\n<tr><td align="center">'
        _n = "%s_opt%d" % (name, ix)
        if last.get(_n, False):
            _s = ' checked'
            checked.add(_n)
        else:
            _s = ''
        out += '<input type="checkbox" name="%s" value="%s"%s />' % (_n, ix,
                                                                     _s)
        text = csm_language.source_transform_string(info, i)
        out += '</td><td>%s</td></tr>' % text
    out += '\n</table>'
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (name, name,
                                                                   last or '')
    checked_str = ','.join(('%r: true' % i) for i in checked)
    out += (
        '\n<script type="text/javascript">'
        '\nvar %s_selected = {%s};'
        '\n$("#%s").val(JSON.stringify(%s_selected));'
        '\n$("input:checkbox[name^=%s_opt]").click(function(){'
        '\n    %s_selected[$(this).attr("name")] = $(this).prop("checked");'
        '\n    $("#%s").val(JSON.stringify(%s_selected));});'
        '\n</script>') % ((info['csq_name'],
                           checked_str, ) + (info['csq_name'], ) * 6)
    return out


def render_html_radio(last_log, **info):
    if last_log is None:
        last_log = {}
    out = '<table border="0">'
    name = info['csq_name']
    last = last_log.get(info['csq_name'], None)
    for (ix, i) in enumerate(info['csq_options']):
        out += '\n<tr><td align="center">'
        if last == str(ix):
            _s = ' checked'
        else:
            _s = ''
        out += '<input type="radio" name="%s_opts" value="%s"%s />' % (name,
                                                                       ix, _s)
        text = csm_language.source_transform_string(info, i)
        out += '</td><td>%s</td></tr>' % text
    out += '\n</table>'
    out += '<input type="hidden" name="%s" id="%s" value="%s">' % (name, name,
                                                                   last or '')
    out += ('\n<script type="text/javascript">'
            '\n$("input:radio[name=%s_opts]").click(function(){'
            '\n    $("#%s").val($(this).val());});'
            '\n</script>') % (info['csq_name'], info['csq_name'])
    return out


_renderers = {
    'dropdown': render_html_dropdown,
    'radio': render_html_radio,
    'checkbox': render_html_checkbox,
}


def answer_display(**info):
    soln = info['csq_soln']
    if info['csq_multiplechoice_soln_mode'] != 'value':
        soln = info['csq_options'][soln]
    out = "Solution: %s" % (soln, )
    return out
