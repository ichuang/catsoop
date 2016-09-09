# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

tutor.qtype_inherit('bigbox')

_base_render_html = render_html

defaults.update({
    'csq_soln': '',
    'csq_npoints': 1,
    'csq_show_check': False,
})


def markdownify(context, text):
    return context['csm_loader']._md(text)


def richtext_format(context, text, msg="Preview:"):
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    out = '</br>%s<br/>' % msg
    out += ('<div style="background-color: #eeeeee;'
            'padding:10px; border-radius:10px;">')
    out += markdownify(context, text)
    out += ('<script type="text/javascript">'
            'catsoop.render_all_math($("#cs_qdiv_%s"), true);'
            '</script>') % context['csq_name']
    out += '</div>'
    return out


checktext = "Preview"


def handle_check(submission, **info):
    last = submission.get(info['csq_name'])
    return richtext_format(info, last)


def render_html(last_log, **info):
    out = _base_render_html(last_log, **info)
    help_url = '/'.join([info['cs_url_root'], '__QTYPE__', 'richtext',
                         'formatting.html'])
    out += ('''<a onClick="window.open('%s', '_blank', '''
            ''''');" '''
            '''style="cursor:pointer; cursor:hand;">'''
            '''Formatting Help</a>''') % help_url
    return out
