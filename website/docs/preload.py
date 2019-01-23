import os
import subprocess

from datetime import datetime

cs_long_name = 'Documentation'

docs_loc = os.path.join(cs_data_root, 'courses', cs_course, 'docs')
cs_title = 'Documentation | CAT-SOOP'

cs_top_menu = [{'text': 'Navigation', 'link': [

    {'link': "COURSE", 'text': 'CAT-SOOP Home'},
    {'link': "COURSE/docs", 'text': 'Docs Home'},
    {'link': "COURSE/docs/about", 'text': 'About'},
    {'link': "COURSE/docs/installing", 'text': 'Installing'},
    {'link': "COURSE/docs/authoring", 'text': 'Authoring'},
    {'link': "COURSE/docs/extending", 'text': 'Extending'},
    {'link': "COURSE/docs/contributing", 'text': 'Contributing'},
    {'link': "COURSE/docs/api/catsoop", 'text': 'API'},

]}]

def callout(note, header, style):
    return """<div class="callout callout-%s">
<h4>%s</h4>
%s
</div>""" % (style, header, csm_language._md_format_string(globals(), note))

def note(x):
    cs_print(callout(x, "Note", "info"))
    return ''

def warning(x):
    cs_print(callout(x, "Warning", "danger"))
    return ''

def doublecheck(x):
    cs_print(callout(x, "Double Check", "warning"))
    return ''

def aside(x):
    cs_print(callout(x, "Aside", "warning"))
    return ''

todo = '''<div class="callout callout-danger">
<p>
  <b>This Page Needs Attention</b>
</p>
<p>
  Contributions to documentation are more than welcome!
  You can e-mail contributions (or questions) to
  <code>~adqm/catsoop-dev@lists.sr.ht</code>.
</p>
</div>'''
