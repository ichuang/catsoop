# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

base, _ = tutor.question('bigbox')

defaults = dict(base['defaults'])
defaults.update({
    'csq_soln': '',
    'csq_npoints': 1,
    'csq_show_check': False,
})

render_html = base['render_html']
total_points = base['total_points']
answer_display = base['answer_display']


def markdownify(context, text):
    return context['csm_loader']._md(text)


def richtext_format(context, text, msg="Preview:"):
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    out = '</br>%s<br/>' % msg
    out += ('<div style="background-color: #eeeeee;'
            'padding:10px; border-radius:10px;">')
    out += markdownify(context, text)
    out += ('<script type="text/javascript">'
            'cs_render_all_math($("#cs_qdiv_%s"), true);'
            '</script>') % context['csq_name']
    out += '</div>'
    return out


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
    msg += richtext_format(info, sub, "You submitted the following text:")
    return {'score': percent, 'msg': msg}


checktext = "Preview"


def handle_check(submission, **info):
    last = submission.get(info['csq_name'])
    return richtext_format(info, last)


def render_html(last_log, **info):
    out = base['render_html'](last_log, **info)
    help_url = '/'.join([info['cs_url_root'], '__QTYPE__', 'richtext',
                         'formatting.html'])
    out += ('''<a onClick="window.open('%s', '_blank', '''
            ''''toolbar=0,location=0,menubar=0,'''
            '''width=200,height=400');" '''
            '''style="cursor:pointer; cursor:hand;">'''
            '''Formatting Help</a>''') % help_url
    return out
