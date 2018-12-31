# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
"""
Handling of the CAT-SOOP specification language(s): Markdown, XML, and Python

The real goal of parsing of a page's source is to convert it back to the
original Python specification format.  Markdown is translated to XML, which is
translated to Python.  The overall flow when parsing a page is:

1. If the content file is in Markdown, parse it down to HTML.
2. If the content file was in Markdown or XML, parse it down to Python
    (stripping out comments and seperating &lt;question&gt; tags into
    appropriate calls to `catsoop.tutor.question`).
"""

import os
import re
import ast
import sys
import copy
import random
import string
import hashlib
import traceback

from io import StringIO
from collections import OrderedDict

from . import tutor
from . import dispatch
from . import markdown_math
from .errors import html_format, clear_info

import markdown
from markdown.extensions import tables
from markdown.extensions import fenced_code
from markdown.extensions import sane_lists
from bs4 import BeautifulSoup

_nodoc = {
    "BeautifulSoup",
    "OrderedDict",
    "StringIO",
    "clear_info",
    "html_format",
    "PYTHON_REGEX",
    "PYVAR_REGEX",
    "remove_common_leading_whitespace",
    "source_formats",
    "source_format_string",
}

_malformed_question = "<font color='red'>malformed <tt>question</tt></font>"

_valid_qname = re.compile(r"^[_A-Za-z][_A-Za-z0-9]*$")


def xml_pre_handle(context):
    """
    Translate the value in `cs_content` from XML to Python, storing the result
    as `cs_problem_spec` in the given context.

    This function mostly strips out comments and converts &lt;question&gt; tags
    into appropriate calls to `catsoop.tutor.question`.

    **Parameters:**

    * `context`: the context associated with this request (from which
      `cs_content` is taken)

    **Returns:** `None`
    """
    text = context["cs_content"]
    text = re.sub(_environment_matcher("comment"), "", text)
    tmp = text.split("<question")
    qcount = 0
    o = [tmp[0]]
    for piece in tmp[1:]:
        chunks = piece.strip().split(">", 1)
        if len(chunks) != 2:
            o.append(_malformed_question)
            break
        type_, rest = chunks
        otherrest = rest.split("</question>", 1)
        if len(otherrest) != 2:
            o.append(_malformed_question)
            break
        code, rest = otherrest
        e = dict(context)
        try:
            code = remove_common_leading_whitespace(code)
            if isinstance(code, int):
                o.append(
                    (
                        "<div><font color='red'><b>A Python Error Occurred:</b></font>"
                        "<p><pre>"
                        "Inconsistent indentation on line %d of question tag"
                        "</pre></p></div>"
                    )
                    % code
                )
                o.append(rest)
                continue
            exec(code, e)
            if "csq_name" not in e:
                e["csq_name"] = "q%06d" % qcount
                qcount += 1
            if _valid_qname.match(e["csq_name"]):
                if type_ != 'dummy':
                    o.append(tutor.question(context, type_, **e))
            else:
                o.append(
                    (
                        '<div class="question">'
                        '<font color="red">'
                        "ERROR: Invalid question name <code>%r</code>"
                        "</font></div>"
                    )
                    % e["csq_name"]
                )
        except:
            e = sys.exc_info()
            tb_entries = traceback.extract_tb(e[2])
            fname, lineno, func, text = tb_entries[-1]
            exc_only = traceback.format_exception_only(e[0], e[1])
            if e[0] == SyntaxError:
                tb_text = "Syntax error in question tag:\n"
            elif func == "<module>":
                tb_text = "Error on line %d of question tag." % lineno
                try:
                    tb_text += "\n    %s\n\n" % code.splitlines()[lineno - 1].strip()
                except:
                    pass
            else:
                tb_text = context["csm_errors"].error_message_content(
                    context, html=False
                )
                exc_only = [""]
            tb_text = "".join([tb_text] + exc_only)

            err = html_format(clear_info(context, tb_text))
            ret = (
                "<div><font color='red'>"
                "<b>A Python Error Occurred:</b>"
                "<p><pre>%s</pre><p>"
                "</font></div>"
            ) % err
            o.append(ret)
        o.append(rest)
    context["cs_problem_spec"] = o


def _md(x):
    o = markdown.markdown(
        x,
        extensions=[
            tables.TableExtension(),
            fenced_code.FencedCodeExtension(),
            sane_lists.SaneListExtension(),
            markdown_math.MathExtension(),
        ],
    )
    return o


def md_pre_handle(context, xml=True):
    """
    Translate the value in `cs_content` from Markdown to HTML

    **Parameters:**

    * `context`: the context associated with this request (from which
      `cs_content` is taken)

    **Optional Parameters:**

    * `xml` (default `True`): whether `catsoop.language.xml_pre_handle` should
      be invoked after translating to HTML

    **Returns:** `None`
    """
    text = context["cs_content"]

    text = re.sub(_environment_matcher("comment"), "", text)

    text = _md_format_string(context, text, False)

    context["cs_content"] = text
    if xml:
        xml_pre_handle(context)


def py_pre_handle(context):
    """
    'Pre-handler' for Python.

    This function exists to mirror the interface of `md_pre_handle` and
    `xml_pre_handle`, but it does nothing (since the `cs_problem_spec` does not
    need any additional processing at this point).

    **Parameters:**

    * `context`: the context associated with this request (from which
      `cs_content` is taken)

    **Returns:** `None`
    """
    pass


def _md_format_string(context, s, xml=True):
    # generate a unique string to split around
    splitter = None
    while splitter is None or splitter in s:
        splitter = "".join(random.choice(string.ascii_letters) for i in range(20))

    # extract tags, replace with splitter
    tag_contents = []

    def _replacer(m):
        tag_contents.append(m.groups())
        return splitter

    tags_to_replace = context.get("cs_markdown_ignore_tags", tuple())
    tags = ("pre", "question", "(?:display)?math", "script") + tuple(tags_to_replace)
    checker = re.compile(
        r"<(%s)(.*?)>(.*?)</\1>" % "|".join(tags), re.MULTILINE | re.DOTALL
    )

    text = re.sub(checker, _replacer, s)

    text = _md(text)

    num_tags = len(tag_contents)
    pieces = text.split(splitter)
    o = ""
    for ix, piece in enumerate(pieces):
        o += piece
        if ix < num_tags:
            t, r, b = tag_contents[ix]
            o += "<%s%s>%s</%s>" % (t, r, b, t)
    text = o

    if text.startswith("<p>") and text.endswith("</p>"):
        text = text[3:-4]

    return _xml_format_string(context, text) if xml else text


def _xml_format_string(context, s):
    return handle_custom_tags(context, s)


source_formats = OrderedDict(
    [("md", md_pre_handle), ("xml", xml_pre_handle), ("py", py_pre_handle)]
)
"""OrderedDict mapping source format names to formatting handlers"""

source_format_string = OrderedDict(
    [("md", _md_format_string), ("xml", _xml_format_string), ("py", _xml_format_string)]
)
"""OrderedDict mapping source format names to formatters"""


def source_transform_string(context, s):
    """
    Convert the given string to HTML, based on the syntax associated with the
    type of the current content file.

    If the content file is Markdown, this will translate the string into HTML
    and handle custom tags.  If the content file is in HTML or Python, custom
    tags will be handled, but no other translation will occur.

    **Parameters:**

    * `context`: the context associated with this request
    * `s`: the string to be translated to HTML

    **Returns:** the translated string
    """
    src_format = context.get("cs_source_format", None)
    if src_format is not None:
        return source_format_string[src_format](context, s)
    else:
        return s


# Handling of custom XML tags


def _environment_matcher(tag):
    return re.compile(
        """<%s>(?P<body>.*?)</%s>""" % (tag, tag),
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )


_matcher = r"[\#0\- +]*\d*(?:.\d+)?[hlL]?[diouxXeEfFgGcrs]"
_matcher = r"(?:%%%s|%s)?" % (_matcher, _matcher)
_pyvar_matcher = r"(?P<lead>^|[^\\])@(?P<fmt>%s){(?P<body>.+?)}" % _matcher
PYVAR_REGEX = re.compile(_pyvar_matcher, re.DOTALL | re.IGNORECASE)
"""Regular expression for matching `@{}` syntax"""

PYTHON_REGEX = re.compile(
    r"""<(?P<tag>python|printf) *(?P<opts>.*?)>(?P<body>.*?)</(?P=tag)>""",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
"""Regular expression for matching &lt;python&gt; tags"""


def remove_common_leading_whitespace(x):
    lines = x.splitlines()
    if len(lines) == 0:
        return ""
    for ix in range(len(lines)):
        if lines[ix].strip():
            break
    first_ix = ix
    candidate = re.match(_indent_regex, lines[first_ix])
    if candidate is None:
        return x
    candidate = candidate.group(1)
    for ix, i in enumerate(lines):
        if ix < first_ix or not i.strip():
            continue
        if not i.startswith(candidate):
            return ix
    lc = len(candidate)
    return "\n".join(i[lc:] for i in lines)


def _tab_replacer(x):
    return x.group(1).replace("\t", "    ")


_indent_regex = re.compile(r"^(\s*)")


def _replace_indentation_tabs(x):
    return re.sub(_indent_regex, _tab_replacer, x)


_string_regex = re.compile(
    r"""(\"\"\"[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*\"\"\"|'''[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''|'[^\n'\\]*(?:\\.[^\n'\\]*)*'|"[^\n"\\]*(?:\\.[^\n"\\]*)*")""",
    re.MULTILINE | re.DOTALL,
)


def indent_code(c):
    strings = {}
    # start by removing strings and replacing them with unique character sequences
    def _replacer(x):
        new_id = None
        while new_id is None or new_id in strings or new_id in c:
            new_id = "".join(random.choice(string.ascii_letters) for i in range(20))
        strings[new_id] = x.group(1)
        return new_id

    c = re.sub(_string_regex, _replacer, c)
    # now that strings are out of the way, change the indentation of every line
    c = "\n".join("    %s" % _replace_indentation_tabs(i) for i in c.splitlines())
    c = "    pass\n%s" % c
    # finally, reintroduce strings
    for k, v in strings.items():
        c = c.replace(k, v)
    return c


def get_python_output(context, code, variables, line_offset=0):
    """
    Helper function.  Evaluate code in the given environment, and return its
    output, if any.

    Makes use of a special variable `cs___WEBOUT`, which is a file-like
    object.  Any data written to `cs___WEBOUT` will be returned.  Overwrites
    `print` in the given environment so that it outputs to `cs___WEBOUT`
    instead of to stdout.

    **Parameters:**

    * `context`: the context associated with this request
    * `code`: a strin containing the Python code to be executed
    * `variables`: a dictionary representing the environment in which the code
        should be executed

    **Optional Parameters**:

    * `line_offset` (default `0`): the offset, in lines, of this code's
        &lt;python&gt; tag from the top of the source file; used in case an error
        occurs, to try to point authors to the right location in the original
        source file

    **Returns:** a string containing any values written to `cs___WEBOUT`
    """
    variables.update({"cs___WEBOUT": StringIO()})
    try:
        code = remove_common_leading_whitespace(code)
        if isinstance(code, int):
            return (
                "<div><font color='red'><b>A Python Error Occurred:</b></font>"
                "<p><pre>"
                "Inconsistent indentation on line %d of python tag (line %d of source)"
                "</pre></p></div>"
            ) % (code, code + line_offset + 1)
        code = indent_code(code)
        code = (
            (
                "_cs_oprint = print\n"
                "def myprint(*args, **kwargs):\n"
                '    if "file" not in kwargs:\n'
                '        kwargs["file"] = cs___WEBOUT\n'
                "    _cs_oprint(*args, **kwargs)\n"
                "print = cs_print = myprint\n"
                "try:\n\n"
            )
            + code
            + (
                "\nexcept Exception as e:\n"
                "    raise e\n"
                "finally:\n"
                "    print = _cs_oprint"
            )
        )
        code = code.replace("tutor.init_random()", "tutor.init_random(globals())")
        code = code.replace("tutor.question(", "tutor.question(globals(),")
        exec(code, variables)
        return variables["cs___WEBOUT"].getvalue()
    except:
        e = sys.exc_info()
        tb_entries = traceback.extract_tb(e[2])
        fname, lineno, func, text = tb_entries[-1]
        exc_only = traceback.format_exception_only(e[0], e[1])
        if e[0] == SyntaxError:
            tb_text = "Syntax error in Python tag:\n"

            def lineno_replacer(x):
                return "line %d" % (ast.literal_eval(x.group(1)) - 9)

            exc_only = [re.sub(r"line (\d)+", lineno_replacer, i) for i in exc_only]
        elif func == "<module>":
            tb_text = (
                "Error on line %d of Python tag (line %d of source):\n    %s\n\n"
                % (
                    lineno - 9,
                    lineno + line_offset - 8,
                    code.splitlines()[lineno - 1].strip(),
                )
            )
        else:
            tb_text = context["csm_errors"].error_message_content(context, html=False)
            exc_only = [""]
        tb_text = "".join([tb_text] + exc_only)

        err = html_format(clear_info(context, tb_text))
        ret = (
            "<div><font color='red'>"
            "<b>A Python Error Occurred:</b>"
            "<p><pre>%s</pre><p>"
            "</font></div>"
        ) % (err,)
        return ret


def _make_python_handler(context, fulltext):
    if "cs__python_envs" not in context:
        context["cs__python_envs"] = {}

    def python_tag_handler(match):
        execcontext = context
        guess_line = fulltext[: match.start()].count("\n")
        #       guess_line = 0
        d = match.groupdict()
        opts = (d["opts"] or "").strip().split(" ")
        body = d["body"]
        if d["tag"] == "printf":
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
                envname = "=".join(i.split("=")[1:])
                if envname not in context["cs__python_envs"]:
                    context["cs__python_envs"][envname] = {}
                execcontext = context["cs__python_envs"][envname]
        # run the code
        code_result = get_python_output(context, body, execcontext, guess_line)
        # decide whether to show the result
        return (out + code_result).strip() if "noresult" not in opts else (out).strip()

    return python_tag_handler


def handle_includes(context, text):
    """
    Handles all `<include>` tags in the provided text, replacing them with the
    contents of the files they reference.

    **Parameters:**

    * `context`: the context associated with this request
    * `text`: a string containing the raw HTML source of the page

    **Returns:** a string representing the updated HTML after includes have
    been handled
    """
    # we'll handle paths relative to here unless given an absolute path
    def _include_handler(match):
        base_dir = dispatch.content_file_location(context, context["cs_path_info"])
        base_dir = os.path.realpath(os.path.dirname(base_dir))
        b = match.groupdict()["body"]
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
        return "\n\n".join(replacements)

    return re.sub(_environment_matcher("include"), _include_handler, text)


def handle_python_tags(context, text):
    """
    Process all Python-related custom tags.

    Firstly, each `@{}` is translated into an appropriate `<printf>` tag.
    Then, `<python>` and `<printf>` tags are handled sequentially, each being
    replaced with its output after having its code evaluated in the current
    context (using `catsoop.language.get_python_output`).

    **Parameters:**

    * `context`: the context associated with this request
    * `text`: a string containing the raw HTML source of the page

    **Returns:** a string representing the updated HTML after python tags have
    been handled
    """

    def printf_handler(x):
        g = x.groupdict()
        return "%s<printf %s>%s</printf>" % (
            g.get("lead", ""),
            g.get("fmt", None) or "%s",
            g["body"],
        )

    text = re.sub(PYVAR_REGEX, printf_handler, text)
    text = re.sub(PYTHON_REGEX, _make_python_handler(context, text), text)
    return text.replace(r"\@{", "@{")


def handle_custom_tags(context, text):
    """
    Process custom HTML tags

    This function begins by calling `cs_course_handle_custom_tags` on the input
    text, so that courses can implement their own custom HTML tags.  This
    function is responsible for handling the following custom tags:

    * `<chapter>`, `<section>`, `<subsection>`, etc.
    * `<chapter*>`, `<section*>`, etc.
    * `<ref>`
    * `<tableofcontents/>`
    * `<footnote>`
    * `<showhide>`
    * `<math>` and `<displaymath>`

    It also takes care of making sure links, images, etc are referencing real
    URLs instead of internal URLs, and also for making sure that syntax
    highlighting is approprtiately applied for code snippets.

    It is not responsible for handling Python tags or includes (which are
    handled elsewhere, before this function is invoked).

    **Parameters:**

    * `context`: the context associated with this request
    * `text`: a string containing the raw HTML source of the page, after
        running through the handler

    **Returns:** a string representing the updated HTML after custom tags have
    been handled
    """

    if "cs_course_handle_custom_tags" in context:
        text = context["cs_course_handle_custom_tags"](text)

    section = r"((?:chapter)|(?:(?:sub){0,2}section))"
    section_star = r"<(?P<tag>%s)\*>(?P<body>.*?)</(?P=tag)\*?>" % section
    section_star = re.compile(section_star, re.MULTILINE | re.DOTALL | re.IGNORECASE)

    tag_map = {
        "section": ("h2", 1),
        "subsection": ("h3", 2),
        "subsubsection": ("h4", 3),
    }

    def _section_star_matcher(x):
        d = x.groupdict()
        t = d["tag"].rstrip("*")
        b = d["body"]
        t = tag_map[t][0]
        return "<%s>%s</%s>" % (t, b, t)

    text = re.sub(section_star, _section_star_matcher, text)

    tree = BeautifulSoup(text, "html.parser")

    # handle sections, etc.

    labels = {}
    textsections = [0, 0, 0]
    chapter = None
    toc_sections = []

    for i in tree.find_all(re.compile(section)):
        if i.name == "chapter":
            chapter = i.attrs.get("num", "0")
            tag = "h1"
            num = str(chapter)
        else:
            if i.name == "section":
                textsections[0] += 1
                textsections[1] = 0
            elif i.name == "subsection":
                textsections[1] += 1
                textsections[2] = 0
            elif i.name == "subsubsection":
                textsections[2] += 1
            tag, lim = tag_map[i.name]
            to_num = textsections[:lim]
            if chapter is not None:
                to_num.insert(0, chapter)
            num = ".".join(map(str, to_num))

        linknum = num.replace(".", "_")
        linkname = "catsoop_section_%s" % linknum

        lbl = i.attrs.get("label", None)
        if lbl is not None:
            labels[lbl] = {
                "type": i.name,
                "number": num,
                "title": i.string,
                "link": "#%s" % linkname,
            }
        toc_sections.append((num, linkname, i))
        sec = copy.copy(i)
        sec.name = tag
        sec.insert(0, "%s) " % num)
        if lbl is not None:
            sec.attrs["id"] = "catsoop_label_%s" % lbl
        i.replace_with(sec)
        link = tree.new_tag("a")
        link["class"] = "anchor"
        link.attrs["name"] = linkname
        sec.insert_before(link)

    # handle refs

    for i in tree.find_all("ref"):
        if "label" not in i.attrs:
            lbl = list(i.attrs.keys())[0]
        else:
            lbl = i.attrs["label"]

        body = i.innerHTML or '<a href="{link}">{type} {number}</a>'
        body = body.format(**labels[lbl])
        new = BeautifulSoup(body, "html.parser")
        i.replace_with(new)

    # handle table of contents

    for ix, i in enumerate(tree.find_all("tableofcontents")):
        o_toc_dom = toc_dom = tree.new_tag("ul")
        last_handled_len = 0
        first_section = None
        for (num, ref, elt) in toc_sections:
            n = len(num.strip().split("."))  # number of layers deep
            if n > last_handled_len and last_handled_len != 0:
                # want a new level of indentation
                ltoc_dom = toc_dom
                toc_dom = tree.new_tag("ul")
                ltoc_dom.append(toc_dom)
            while n < last_handled_len:
                toc_dom = toc_dom.parent
                last_handled_len -= 1
            last_handled_len = n
            toc_entry = tree.new_tag("li")
            link = copy.copy(elt)
            link.name = "a"
            link["href"] = "#%s" % ref
            link.insert(0, "%s) " % num)
            toc_entry.append(link)
            toc_dom.append(toc_entry)

        toc_sec = tree.new_tag("h2")
        toc_sec.string = "Table of Contents"
        i.replace_with(toc_sec)
        toc_sec.insert_after(o_toc_dom)

    # footnotes

    footnotes = []

    for ix, i in enumerate(tree.find_all("footnote")):
        jx = ix + 1
        footnotes.append(i.decode_contents())
        sup = tree.new_tag("sup")
        sup.string = str(jx)
        i.replace_with(sup)
        link = tree.new_tag("a", href="#catsoop_footnote_%d" % jx)
        sup.wrap(link)
        ref = tree.new_tag("a")
        ref.attrs["name"] = "catsoop_footnote_ref_%d" % jx
        ref["class"] = "anchor"
        link.insert_before(ref)

    if len(footnotes) == 0:
        fnote = ""
    else:
        fnote = '<br/>&nbsp;<hr/><b name="cs_footnotes">Footnotes</b>'
        for (ix, f) in enumerate(footnotes):
            ix = ix + 1
            fnote += (
                '<p><a class="anchor" name="catsoop_footnote_%d"></a><sup style="padding-right:0.25em;color:var(--cs-base-bg-color);">%d</sup>'
                '%s <a href="#catsoop_footnote_ref_%d">'
                '<span class="noprint">(click to return to text)</span>'
                "</a></p>"
            ) % (ix, ix, f, ix)
    context["cs_footnotes"] = fnote

    # hints (<showhide>)

    def _md5(x):
        return hashlib.md5(x.encode()).hexdigest()

    for ix, i in enumerate(tree.find_all("showhide")):
        i.name = "div"
        i.attrs["style"] = "display:none;"
        wrap = tree.new_tag("div")
        wrap["class"] = ["response"]
        i.wrap(wrap)
        #        button = tree.new_tag('button', onclick="function(){var x=document.getElementById(%r);if(x.style.indexOf('none')>-1){x.style='display: block';}else{x.style='display:none;'}}" % i.attrs['id'])
        button = tree.new_tag(
            "button",
            onclick="if(this.nextSibling.style.display === 'none'){this.nextSibling.style.display = 'block';}else{this.nextSibling.style.display = 'none';}",
        )
        button.string = "Show/Hide"
        i.insert_before(button)

    # custom URL handling in img, a, script, link

    URL_FIX_LIST = [("img", "src"), ("a", "href"), ("script", "src"), ("link", "href")]

    for (tag, field) in URL_FIX_LIST:
        for i in tree.find_all(tag):
            if field in i.attrs:
                i.attrs[field] = dispatch.get_real_url(context, i.attrs[field])

    # math tags
    handle_math_tags(tree)

    # code blocks: specific default behavior
    default_code_class = context.get("cs_default_code_language", "nohighlight")
    if default_code_class is not None:
        for i in tree.find_all("code"):
            if i.parent.name != "pre":
                continue
            if "class" in i.attrs and (
                isinstance(i.attrs["class"], str) or len(i.attrs["class"]) > 0
            ):
                # this already has a class; skip!
                continue
            i.attrs["class"] = [default_code_class]

    return str(tree)


def handle_math_tags(tree):
    """
    Handles `<math>` and `<displaymath>` tags, replacing them with `<span>` and
    `<div>` elements with appropriate classes so the Javascript math renderer
    can find them.

    **Parameters:**

    * `context`: the context associated with this request
    * `text`: a string containing the raw HTML source of the page

    **Returns:** a string representing the updated HTML after math tags have
    been handled
    """
    for ix, i in enumerate(tree.find_all(re.compile("(?:display)?math"))):
        i["class"] = i.get("class", [])
        if i.name == "math":
            i.name = "span"
        else:
            i.name = "div"
            i.attrs["style"] = "text-align:center;padding-bottom:10px;"
            i["class"].append("cs_displaymath")
        i["class"].append("cs_math_to_render")
    return tree
