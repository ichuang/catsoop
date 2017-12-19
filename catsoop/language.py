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

# Features of the CAT-SOOP specification language(s)

# Handling of XML, MD, PY sources

import os
import re
import sys
import copy
import random
import string
import hashlib
import traceback

from io import StringIO
from collections import OrderedDict
from contextlib import redirect_stdout

from . import tutor
from . import dispatch
from . import markdown_math
from .tools import markdown
from .errors import html_format, clear_info
from .tools.markdown.extensions import tables
from .tools.markdown.extensions import fenced_code
from .tools.markdown.extensions import sane_lists
from .tools.bs4 import BeautifulSoup

_malformed_question = "<font color='red'>malformed <tt>question</tt></font>"


def _xml_pre_handle(context):
    text = context['cs_content']
    text = re.sub(_environment_matcher('comment'), '', text)
    tmp = text.split('<question')
    qcount = 0
    o = [tmp[0]]
    for piece in tmp[1:]:
        chunks = piece.strip().split('>', 1)
        if len(chunks) != 2:
            o.append(_malformed_question)
            break
        type, rest = chunks
        otherrest = rest.split('</question>', 1)
        if len(otherrest) != 2:
            o.append(_malformed_question)
            break
        code, rest = otherrest
        e = dict(context)
        try:
            code = remove_common_leading_whitespace(code)
            if isinstance(code, int):
                raise IndentationError(
                    'Inconsistent indentation on line %d' % code)
            exec(code, e)
            if 'csq_name' not in e:
                e['csq_name'] = 'q%06d' % qcount
                qcount += 1
            o.append(tutor.question(context, type, **e))
        except:
            err = html_format(clear_info(context, traceback.format_exc()))
            ret = ("<div><font color='red'>"
                   "<b>A Python Error Occurred:</b>"
                   "<p><pre>%s</pre><p>"
                   "Please contact staff."
                   "</font></div>") % err
            o.append(ret)
        o.append(rest)
    context['cs_problem_spec'] = o


def _md(x):
    o = markdown.markdown(
        x,
        extensions=[
            tables.TableExtension(),
            fenced_code.FencedCodeExtension(),
            sane_lists.SaneListExtension(),
            markdown_math.MathExtension()
        ])
    return o


def _md_pre_handle(context, xml=True):
    text = context['cs_content']

    text = re.sub(_environment_matcher('comment'), '', text)

    text = _md_format_string(context, text, False)

    context['cs_content'] = text
    if xml:
        _xml_pre_handle(context)


def _py_pre_handle(context):
    pass


def _md_format_string(context, s, xml=True):
    # generate a unique string to split around
    splitter = None
    while splitter is None or splitter in s:
        splitter = ''.join(
            random.choice(string.ascii_letters) for i in range(20))

    # extract tags, replace with splitter
    tag_contents = []

    def _replacer(m):
        tag_contents.append(m.groups())
        return splitter

    tags_to_replace = context.get('cs_markdown_ignore_tags', tuple())
    tags = ('pre', 'question', '(?:display)?math',
            'script') + tuple(tags_to_replace)
    checker = re.compile(r'<(%s)(.*?)>(.*?)</\1>' % '|'.join(tags),
                         re.MULTILINE | re.DOTALL)

    text = re.sub(checker, _replacer, s)

    text = _md(text)

    num_tags = len(tag_contents)
    pieces = text.split(splitter)
    o = ''
    for ix, piece in enumerate(pieces):
        o += piece
        if ix < num_tags:
            t, r, b = tag_contents[ix]
            o += '<%s%s>%s</%s>' % (t, r, b, t)
    text = o

    if text.startswith('<p>') and text.endswith('</p>'):
        text = text[3:-4]

    return _xml_format_string(context, text) if xml else text


def _xml_format_string(context, s):
    return handle_custom_tags(context, s)


source_formats = OrderedDict([('md', _md_pre_handle), ('xml', _xml_pre_handle),
                              ('py', _py_pre_handle)])
"""OrderedDict mapping source format names to formatting handlers"""

source_format_string = OrderedDict([('md', _md_format_string),
                                    ('xml', _xml_format_string),
                                    ('py', _xml_format_string)])
"""OrderedDict mappying source format names to formatters"""


def source_transform_string(context, s):
    """
    Transform the given string according to the source format
    """
    src_format = context.get('cs_source_format', None)
    if src_format is not None:
        return source_format_string[src_format](context, s)
    else:
        return s


# Handling of custom XML tags


def _environment_matcher(tag):
    return re.compile("""<%s>(?P<body>.*?)</%s>""" % (tag, tag),
                      re.MULTILINE | re.DOTALL | re.IGNORECASE)


_matcher = r'[\#0\- +]*\d*(?:.\d+)?[hlL]?[diouxXeEfFgGcrs]'
_matcher = r'(?:%%%s|%s)?' % (_matcher, _matcher)
_pyvar_matcher = r"(?P<lead>^|[^\\])@(?P<fmt>%s){(?P<body>.+?)}" % _matcher
PYVAR_REGEX = re.compile(_pyvar_matcher, re.DOTALL | re.IGNORECASE)
"""Regular expression for matching @{} syntax"""

PYTHON_REGEX = re.compile(
    r"""<(?P<tag>python|printf) *(?P<opts>.*?)>(?P<body>.*?)</(?P=tag)>""",
    re.MULTILINE | re.DOTALL | re.IGNORECASE)
"""Regular expression for matching <python> tags"""


def remove_common_leading_whitespace(x):
    lines = x.splitlines()
    if len(lines) == 0:
        return ''
    for ix in range(len(lines)):
        if lines[ix].strip():
            break
    first_ix = ix
    candidate = re.match(r'^(\s*)', lines[first_ix])
    if candidate is None:
        return x
    candidate = candidate.group(1)
    for ix, i in enumerate(lines):
        if ix < first_ix or not i.strip():
            continue
        if not i.startswith(candidate):
            return ix
    lc = len(candidate)
    return '\n'.join(i[lc:] for i in lines)


def get_python_output(context, code, variables, line_offset):
    '''
    Get output from Python code.

    Makes use of a special variable cs___WEBOUT, which is a file-like
    object.  Any data written to cs___WEBOUT will be returned.  Exposes a
    function cs_print to the code provided, so that cs_print(x) will
    function as print(x, file=cs___WEBOUT).

    Writing code to stdout (as with a normal print statement) will not work.
    '''
    variables.update({'cs___WEBOUT': StringIO()})
    try:
        code = remove_common_leading_whitespace(code)
        if isinstance(code, int):
            return ("<div><font color='red'><b>A Python Error Occurred:</b></font>"
                    '<p><pre>'
                    'Inconsistent indentation on line %d of python tag (line %d of source)'
                    '</pre></p></div>') % (code, code + line_offset + 1)
        code = ('_cs_oprint = print\n'
                'def myprint(*args, **kwargs):\n'
                '    if "file" not in kwargs:\n'
                '        kwargs["file"] = cs___WEBOUT\n'
                '    _cs_oprint(*args, **kwargs)\n'
                'print = cs_print = myprint\n\n') + code + '\n\nprint = _cs_oprint'
        code = code.replace('tutor.init_random()',
                            'tutor.init_random(globals())')
        code = code.replace('tutor.question(', 'tutor.question(globals(),')
        exec(code, variables)
        return variables['cs___WEBOUT'].getvalue()
    except:
        e = sys.exc_info()
        tb_entries = traceback.extract_tb(e[2])
        fname, lineno, func, text = tb_entries[-1]
        tb_text = 'Error on line %d of python tag (line %d of source):\n    %s\n\n' % (lineno - 8, lineno + line_offset - 7, code.splitlines()[lineno-1].strip())
        tb_text = ''.join([tb_text] + traceback.format_exception_only(e[0], e[1]))

        err = html_format(clear_info(context, tb_text))
        ret = ("<div><font color='red'>"
               "<b>A Python Error Occurred:</b>"
               "<p><pre>%s</pre><p>"
               "</font></div>") % (err, )
        return ret


def _make_python_handler(context, fulltext):
    if 'cs__python_envs' not in context:
        context['cs__python_envs'] = {}

    def python_tag_handler(match):
        execcontext = context
        guess_line = fulltext[:match.start()].count('\n')
 #       guess_line = 0
        d = match.groupdict()
        opts = (d['opts'] or "").strip().split(" ")
        body = d['body']
        if d['tag'] == 'printf':
            if len(opts) == 1 and opts[0] == "":
                f = "%s"
            else:
                f = opts[0]
            body = "print(%r %% (%s,))" % (f, body)
            opts = []
        out = ""
        # decide whether to show the code
        if "show" in opts:
            opts.remove("show")
            code = '<pre><code class="lang-python">%s</code></pre>'
            out += code % html_format(body)
        # decide whether to run the code
        if "norun" in opts:
            return (out).strip()
        # decide in which environment the code should be run
        for i in opts:
            if i.startswith("env="):
                envname = "=".join(i.split('=')[1:])
                if envname not in context['cs__python_envs']:
                    context['cs__python_envs'][envname] = {}
                execcontext = context['cs__python_envs'][envname]
        # run the code
        code_result = get_python_output(context, body, execcontext, guess_line)
        # decide whether to show the result
        return ((out + code_result).strip()
                if "noresult" not in opts else (out).strip())

    return python_tag_handler


def handle_includes(context, text):
    # we'll handle paths relative to here unless given an absolute path
    def _include_handler(match):
        base_dir = dispatch.content_file_location(context, context['cs_path_info'])
        base_dir = os.path.realpath(os.path.dirname(base_dir))
        b = match.groupdict()['body']
        replacements = []
        for fname in b.splitlines():
            fname = fname.strip()
            if not fname:
                continue  # skip blank lines
            fname = os.path.join(base_dir, fname)
            fname = os.path.realpath(fname)
            if os.path.commonprefix([fname, base_dir]) != base_dir:
                # tried to escape the course
                continue
            if not os.path.isfile(fname):
                continue
            with open(fname) as f:
                replacements.append(f.read())
        return '\n\n'.join(replacements)
    return re.sub(_environment_matcher('include'), _include_handler, text)


def handle_python_tags(context, text):
    '''
    Process <python> and <printf> tags.
    '''

    def printf_handler(x):
        g = x.groupdict()
        return '%s<printf %s>%s</printf>' % (g.get('lead', ''),
                                             g.get('fmt', None) or '%s',
                                             g['body'])

    text = re.sub(PYVAR_REGEX, printf_handler, text)
    text = re.sub(PYTHON_REGEX, _make_python_handler(context, text), text)
    return text.replace(r'\@{', '@{')


def handle_custom_tags(context, text):
    '''
    Process custom HTML tags using fix_single.
    '''

    if 'cs_course_handle_custom_tags' in context:
        text = context['cs_course_handle_custom_tags'](text)


    section = r"((?:chapter)|(?:(?:sub){0,2}section))"
    section_star = r"<(?P<tag>%s)\*>(?P<body>.*?)</(?P=tag)\*?>" % section
    section_star = re.compile(section_star,
                              re.MULTILINE | re.DOTALL | re.IGNORECASE)

    tag_map = {
        'section': ('h2', 1),
        'subsection': ('h3', 2),
        'subsubsection': ('h4', 3),
    }

    def _section_star_matcher(x):
        d = x.groupdict()
        t = d['tag'].rstrip('*')
        b = d['body']
        t = tag_map[t][0]
        return '<%s>%s</%s>' % (t, b, t)
    text = re.sub(section_star, _section_star_matcher, text)

    tree = BeautifulSoup(text, 'html.parser')

    # handle sections, etc.

    labels = {}
    textsections = [0, 0, 0]
    chapter = None


    for i in tree.find_all(re.compile(section)):
        if i.name == 'chapter':
            chapter = i.attrs.get('num', '0')
            tag = 'h1'
            num = str(chapter)
        else:
            if i.name == 'section':
                textsections[0] += 1
                textsections[1] = 0
            elif i.name == 'subsection':
                textsections[1] += 1
                textsections[2] = 0
            elif i.name == 'subsubsection':
                textsections[2] += 1
            tag, lim = tag_map[i.name]
            to_num = textsections[:lim]
            if chapter is not None:
                to_num.insert(0, chapter)
            num = '.'.join(map(str, to_num))

        linknum = num.replace('.', '_')
        linkname = "catsoop_section_%s" % linknum

        lbl = i.attrs.get('label', None)
        if lbl is not None:
            labels[lbl] = {
                'type': i.name,
                'number': num,
                'title': i.string,
                'link': '#%s' % linkname
            }
        sec = copy.copy(i)
        sec.name = tag
        sec.insert(0, '%s) ' % num)
        if lbl is not None:
            sec.attrs['id'] = 'catsoop_label_%s' % lbl
        i.replace_with(sec)
        link = tree.new_tag('a')
        link.attrs['name'] = linkname
        sec.insert_before(link)

    # handle refs

    for i in tree.find_all('ref'):
        if 'label' not in i.attrs:
            lbl = list(i.attrs.keys())[0]
        else:
            lbl = i.attrs['label']

        body = i.innerHTML or '<a href="{link}">{type} {number}</a>'
        body = body.format(**labels[lbl])
        new = BeautifulSoup(body, 'html.parser')
        i.replace_with(new)

    # footnotes

    footnotes = []

    for ix, i in enumerate(tree.find_all('footnote')):
        jx = ix + 1
        footnotes.append(i.decode_contents())
        sup = tree.new_tag('sup')
        sup.string = str(jx)
        i.replace_with(sup)
        link = tree.new_tag('a', href="#catsoop_footnote_%d" % jx)
        sup.wrap(link)
        ref = tree.new_tag('a')
        ref.attrs['name'] = "catsoop_footnote_ref_%d" % jx
        link.insert_before(ref)

    if len(footnotes) == 0:
        fnote = ''
    else:
        fnote = '<br/>&nbsp;<hr/><b name="cs_footnotes">Footnotes</b>'
        for (ix, f) in enumerate(footnotes):
            ix = ix + 1
            fnote += ('<p><a name="catsoop_footnote_%d"><sup>%d</sup> </a>'
                      '%s <a href="#catsoop_footnote_ref_%d">'
                      '<span class="noprint">(click to return to text)</span>'
                      '</a></p>') % (ix, ix, f, ix)
    context['cs_footnotes'] = fnote

    # hints (<showhide>)

    def _md5(x):
        return hashlib.md5(x.encode()).hexdigest()

    for ix, i in enumerate(tree.find_all('showhide')):
        i.name = 'div'
        i.attrs['id'] = "cs_showhide_%s" % _md5(str(i))
        i.attrs['style'] = "display:none;"
        wrap = tree.new_tag('div')
        wrap['class'] = ['response']
        i.wrap(wrap)
        button = tree.new_tag(
            'button', onclick="$('#%s').toggle();" % i.attrs['id'])
        button.string = 'Show/Hide'
        i.insert_before(button)

    # custom URL handling in img, a, script, link

    URL_FIX_LIST = [('img', 'src'), ('a', 'href'), ('script', 'src'), ('link',
                                                                       'href')]

    for (tag, field) in URL_FIX_LIST:
        for i in tree.find_all(tag):
            if field in i.attrs:
                i.attrs[field] = dispatch.get_real_url(context, i.attrs[field])

    # math tags
    handle_math_tags(tree)

    # code blocks: specific default behavior
    default_code_class = context.get('cs_default_code_language', 'nohighlight')
    if default_code_class is not None:
        for i in tree.find_all('code'):
            if i.parent.name != 'pre':
                continue
            if ('class' in i.attrs and (isinstance(i.attrs['class'], str) or
                                        len(i.attrs['class']) > 0)):
                # this already has a class; skip!
                continue
            i.attrs['class'] = [default_code_class]

    return str(tree)


def handle_math_tags(tree):
    for ix, i in enumerate(tree.find_all(re.compile('(?:display)?math'))):
        i['class'] = i.get('class', [])
        if i.name == 'math':
            i.name = 'span'
        else:
            i.name = 'div'
            i.attrs['style'] = "text-align:center;padding-bottom:10px;"
            i['class'].append('cs_displaymath')
        i['class'].append('cs_math_to_render')
    return tree
