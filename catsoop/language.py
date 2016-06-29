def _environment_matcher(tag):
    return re.compile("""<%s>(?P<body>.*?)</%s>""" % (tag, tag), re.MULTILINE |
                      re.DOTALL | re.IGNORECASE)


PYVAR_REGEX = re.compile(r"(?P<lead>^|[^\\])@(?P<fmt>%[^{]+)?{(?P<body>.+?)}",
                         re.DOTALL | re.IGNORECASE)

PYTHON_REGEX = re.compile(
    r"""<(?P<tag>python|printf) *(?P<opts>.*?)>(?P<body>.*?)</(?P=tag)>""",
    re.MULTILINE | re.DOTALL | re.IGNORECASE)
"""Regular expression for matching C{<python>} tags"""

FOOTNOTE_REGEX = _environment_matcher('footnote')
"""Regular expression matching C{<footnote>} tags"""

_ref_regex = r"<ref *?(?P<label>.*?) *?>(?P<body>.*?)</ref>"
REF_REGEX = re.compile(_ref_regex, re.MULTILINE | re.DOTALL | re.IGNORECASE)
"""Regular expression for matching C{ref} tags."""

_section_regex = (r"""<(?P<type>(?:chapter)|(?:(?:sub){0,2}section))\s*?"""
                  r"""(?:(?P<var1>(?:label)|(?:num))=(?P<quote>["'])"""
                  r"""(?P<val1>.*?)(?P=quote))?\s*?"""
                  r"""(?:(?P<var2>(?:label)|(?:num))=(?P<quote2>["'])"""
                  r"""(?P<val2>[^\s]*?)(?P=quote2))?\s*>"""
                  r"""(?P<name>.*?)</(?P=type)>""")
SECTION_REGEX = re.compile(_section_regex, re.MULTILINE | re.DOTALL |
                           re.IGNORECASE)
"""Regular expression for matching C{section} tags."""


def _compiler(inp):
    (x, y) = inp
    compiled = re.compile(x, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return (compiled, y)


REGEX_LIST = map(_compiler,
                 # img tags
                 [(("<img(?P<lead>[^>]*?)src="
                    "(?P<quote>[\"'])(?P<url>.*?)(?P=quote)(?P<trail>.*?)/?>"),
                   '<img{lead}src="{url}"{trail}/>'),
                  # a tags
                  (("<a(?P<lead>[^>]*?)href="
                    "(?P<quote>[\"'])(?P<url>.*?)(?P=quote)"
                    "(?P<trail>.*?)>(?P<body>.*?)</a>"),
                   '<a{lead}href="{url}"{trail}>{body}</a>'),
                  # script tags
                  (("<script(?P<lead>[^>]*?)src="
                    "(?P<quote>[\"'])(?P<url>.*?)(?P=quote)"
                    "(?P<trail>.*?)>(?P<body>.*?)</script>"),
                   '<script{lead}src="{url}"{trail}>{body}</script>'),
                  # link tags
                  (("<link(?P<lead>[^>]*?)href="
                    "(?P<quote>[\"'])(?P<url>.*?)(?P=quote)(?P<trail>.*?)/?>"),
                   '<link{lead}href="{url}"{trail}/>')])
"""
List containing tuples C{(regex,gen)}, where C{regex} is a regular expresion
matching a particular HTML tag, and C{gen} is a string used to generate
processed versions of the same tag.
"""


def html_format(string):
    """
    @return: An HTML-escaped version of the input string, suitable for
    insertion into a <pre> tag
    """
    for x, y in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('\t', '    '),
                 (' ', '&nbsp;')):
        string = string.replace(x, y)
    return string


def get_python_output(context, code, variables):
    '''
    Get output from Python code.

    Makes use of a special variable C{cs___WEBOUT}, which is a file-like
    object.  Any data written to C{cs___WEBOUT} will be returned.  Exposes a
    function C{cs_print} to the code provided, so that C{cs_print(x)} will
    function as C{print >> cs___WEBOUT, x}.

    Writing code to C{stdout} (as with a normal C{print} statement) will not
    work.

    @param code: The Python code to be executed
    @param variables: A dictionary containing variable mappings available to
    the code.  Note that the names C{cs___WEBOUT} and
    C{cs_print} will be overwritten every time this function
    is called.
    @return: Any data written to C{cs___WEBOUT} by the code provided, or an
    error message
    '''
    variables.update({'cs___WEBOUT': StringIO()})
    try:
        code = 'def cs_print(*args):\n    print(*args, file=cs___WEBOUT)\n\n' + code
        code = code.replace('tutor.init_random()',
                            'tutor.init_random(globals())')
        code = code.replace('tutor.question(', 'tutor.question(globals(),')
        exec(code, variables)
        return variables['cs___WEBOUT'].getvalue()
    except:
        err = html_format(clear_info(context, traceback.format_exc()))
        ret = ("<div><font color='red'>"
               "<b>A Python Error Occurred:</b>"
               "<p><pre>%s</pre><p>"
               "Please contact staff."
               "</font></div>") % err
        return ret


def _make_python_handler(context):
    if 'cs__python_envs' not in context:
        context['cs__python_envs'] = {}

    def python_tag_handler(match):
        execcontext = context
        d = match.groupdict()
        opts = (d['opts'] or "").strip().split(" ")
        body = d['body'].strip()
        if d['tag'] == 'printf':
            if len(opts) == 1 and opts[0] == "":
                f = "%s"
            else:
                f = opts[0]
            body = "cs_print(%r %% (%s,))" % (f, body)
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
        code_result = get_python_output(context, body, execcontext)
        # decide whether to show the result
        return ((out + code_result).strip()
                if "noresult" not in opts else (out).strip())

    return python_tag_handler


def handle_python_tags(context, text):
    '''
    Process C{<python>} and C{<printf>} tags.

    @param context: The data associated with this request
    @param text: The raw HTML
    @return: The processed HTML, after handling python tags
    '''

    def printf_handler(x):
        g = x.groupdict()
        return '%s<printf %s>%s</printf>' % (
            g.get('lead', ''), g.get('fmt', None) or '%s', g['body'])

    text = re.sub(PYVAR_REGEX, printf_handler, text)
    text = re.sub(PYTHON_REGEX, _make_python_handler(context), text)
    return text.replace(r'\@{', '@{')


def handle_custom_tags(context, text):
    '''
    Process custom HTML tags using L{fix_single}.

    @param context: The data associated with this request
    @param text: The raw HTML, possibly containing internal links, etc
    @return: The processed HTML, after handling custom tags, and replacing
    internal links with URI's
    '''

    text = re.sub(_environment_matcher('comment'), '', text)

    if 'cs_course_handle_custom_tags' in context:
        text = context['cs_course_handle_custom_tags'](text)

    if context.get('cs_course', None) is not None:
        path = context['cs_path_info'][1:]
        direc = os.path.join(context['cs_data_root'], 'courses',
                             context['cs_course'])
        for ix, i in enumerate(path):
            try:
                direc = os.path.join(direc, loader.get_directory_name(
                    context, context['cs_course'], path[:ix], i))
            except:
                break
        direc = os.path.join(direc, '__MEDIA__')

    # handle sections, etc.
    labels = {}
    textsections = [0, 0, 0]
    chapter = ['None']

    def do_section(match):
        d = match.groupdict()
        t = d['type']
        b = d['name']
        x = {d.get('var1', ''): d.get('val1', ''),
             d.get('var2', ''): d.get('val2', '')}
        r = x.get('label', '')
        if t == 'chapter':
            chapter[0] = str(x.get('num'))
            d['tag'] = 'h1'
            d['num'] = str(chapter[0])
        if t == 'section':
            textsections[0] += 1
            textsections[1] = 0
            d['tag'] = 'h2'
            to_num = [textsections[0]]
            if chapter[0] != 'None':
                to_num.insert(0, chapter[0])
            d['num'] = '.'.join(map(str, to_num))
        if t == 'subsection':
            textsections[1] += 1
            textsections[2] = 0
            to_num = textsections[:-1]
            if chapter[0] != 'None':
                to_num.insert(0, chapter[0])
            d['num'] = '.'.join(map(str, to_num))
            d['tag'] = 'h3'
        if t == 'subsubsection':
            textsections[2] += 1
            to_num = textsections[:]
            if chapter[0] != 'None':
                to_num.insert(0, chapter[0])
            d['num'] = '.'.join(map(str, to_num))
            d['tag'] = 'h3'

        d['usnum'] = d['num'].replace('.', '_')

        if r != '':
            labels[r] = {'type': d['type'],
                         'number': d['num'],
                         'title': d['name'],
                         'link': '#catsoop_section_%s' % d['usnum']}

        return ('<a name="catsoop_section_%(usnum)s"></a>'
                '<%(tag)s>%(num)s) %(name)s</%(tag)s>') % d

    def do_ref(match):
        d = match.groupdict()
        l = d['label'].strip()
        b = d['body'].strip()
        if b == '':
            b = '{number}'
        if l not in labels:
            return '<font color="red">Unknown label: %s</font>' % l
        return b.format(**labels[l])

    text = re.sub(SECTION_REGEX, do_section, text)
    text = re.sub(REF_REGEX, do_ref, text)

    footnotes = []

    def dofootnote(match):
        d = match.groupdict()
        footnotes.append(d['body'])
        n = len(footnotes)
        return ('<a name="catsoop_footnote_ref_%d"></a>'
                '<a href="#catsoop_footnote_%d">'
                '<sup>%d</sup></a>') % (n, n, n)

    text = re.sub(FOOTNOTE_REGEX, dofootnote, text)
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

    hintnum = [0]

    def dohint(match):
        b = match.groupdict().get('body', '')
        h = hintnum[0]
        hintnum[0] += 1
        return ('''<div class="response">'''
                '''<button onclick="$('#cs_showhide_%d').toggle();">'''
                '''Show/Hide</button>'''
                '''<div id="cs_showhide_%d" style="display:none;">%s</div>'''
                '''</div>''') % (h, h, b)

    text = re.sub(_environment_matcher('showhide'), dohint, text)

    for (regex, gen) in REGEX_LIST:
        text = fix_single(context, text, regex, gen)

    math_id = [-1]
    _math_regex = "<(?P<tag>(?:display)?math)>(?P<body>.*?)</(?P=tag)>"
    MATH_REGEX = re.compile(_math_regex, re.MULTILINE | re.DOTALL)

    def math_replacer(m):
        d = m.groupdict()
        b = d.get('body', '')
        t = d.get('tag', '')
        if t == 'math':
            otag = 'span'
        else:
            otag = 'div style="text-align:center;padding-bottom:10px;"'
        math_id[0] += 1
        return '<%s id="cs_math_%06d">%s</%s>' % (otag, math_id[0], b,
                                                  otag.split(' ', 1)[0])

    text = re.sub(MATH_REGEX, math_replacer, text)

    return text
