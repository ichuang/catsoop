# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

import ast
import copy
import hashlib
import json
import os
import random
import re
import string
import sys
import traceback
from io import StringIO

from bs4 import BeautifulSoup, Comment, Doctype
from unidecode import unidecode

from . import dispatch, markdown, tutor
from .errors import clear_info, html_format

_nodoc = {
    "BeautifulSoup",
    "StringIO",
    "clear_info",
    "html_format",
    "indent_code",
    "PYTHON_REGEX",
    "PYVAR_REGEX",
    "remove_common_leading_whitespace",
    "source_formats",
    "source_format_string",
    "unidecode",
}

_malformed_question = "<font color='red'>malformed <tt>question</tt></font>"

_valid_qname = re.compile(r"^[A-Za-z][_A-Za-z0-9]*$")
_unsafe_title = re.compile(r"[^A-Za-z0-9_]")


def _md5(x):
    return hashlib.md5(x.encode("utf-8")).hexdigest()


def _safe_title(t, disallowed=None):
    disallowed = disallowed if disallowed is not None else set()
    title = otitle = "_%s" % (
        re.sub(r"_+", "_", _unsafe_title.sub("_", unidecode(t))).lower().strip("_")
    )
    count = 2
    while title in disallowed:
        title = "%s_%d" % (otitle, count)
        count += 1
    disallowed.add(title)
    return title


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
    names_seen = set()
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
            if e["csq_name"] in names_seen:
                o.append(
                    (
                        '<div class="question">'
                        '<font color="red">'
                        "ERROR: Duplicate question name <code>%r</code>"
                        "</font></div>"
                    )
                    % e["csq_name"]
                )
            elif _valid_qname.match(e["csq_name"]):
                if type_ != "dummy":
                    o.append(tutor.question(context, type_, **e))
                names_seen.add(e["csq_name"])
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
    return markdown.markdown(x)


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

    # remove comments
    text = re.sub(_environment_matcher("comment"), "", text)

    # allow inline markdown processing inside of <div> tags starting with a
    # blank line
    text = re.sub(r"<div([^>]*)>\n\s*?\n", r"<div\1 markdown>\n\n", text)

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


DIAGRAM_START = re.compile(r"\*{5}\**")


def _replace_diagrams(src):
    if not DIAGRAM_START.search(src):
        # try to short-circuit; this is probably faster than splitting and
        # looping in the case where we have no diagrams.
        return src, []

    ix = 0
    lines = src.splitlines(keepends=True)
    diagrams = {}
    while ix < len(lines):
        line = lines[ix]
        match = DIAGRAM_START.search(line)
        if not match:
            ix += 1
            continue

        # if we're here, we found something that looks like the start of a
        # diagram.  look for a match.
        firstline = ix
        firstix, lastix = match.span()
        group = match.group(0)

        jx = ix + 1
        maybe_diagram = False
        lastline = None
        while True:
            if jx >= len(lines):
                # we got here without hitting our terminating condition, so
                # this wasn't actually a diagram.  skip.
                break

            if firstix >= len(lines[jx]) or lines[jx][firstix] != "*":
                # no * on the left hand side; this must not have been a diagram
                # after all.
                break

            if lines[jx][firstix:lastix] == group:
                # this looks like a string of *'s.  we're done, and we found a
                # diagram!
                lastline = (
                    jx + 1
                )  # + 1 so this is exclusive to match span (loops below become easier)
                maybe_diagram = True
                break

            jx += 1

        # if we're out here, we left the loop.  if we're still considering
        # whether something could be a diagram, make sure we've got either a
        # solid border of *'s, or an open right-hand side with nothing beyond
        # the right-most asterisk (this does not quite match Markdeep's
        # heuristic, but I think it makes a lot more sense)

        if maybe_diagram:
            all_closed = True
            trailing_text = False
            leading_text = False
            for l in range(firstline, lastline):
                post = lines[l][lastix:]
                if post and not post.isspace():
                    trailing_text = True

                pre = lines[l][:firstix]
                if pre and not pre.isspace():
                    leading_text = True

                if lastix >= len(lines[l]) or lines[l][lastix - 1] != "*":
                    all_closed = False

            if all_closed or not trailing_text:
                # we found a diagram.  now remove it and replace with a <pre> tag
                # containing the source (our JS will pick this up after the page
                # loads)...

                alignment = "center"
                if leading_text:
                    alignment = "floatright"
                elif trailing_text:
                    alignment = "floatleft"

                diagram_source = []
                term = lastix - 1 if all_closed else lastix
                for l in range(firstline, lastline):
                    if l != firstline and l != lastline - 1:
                        diagram_source.append(lines[l].rstrip("\n")[firstix + 1 : term])
                    lines[l] = (
                        "%s%s" % (lines[l][:firstix], lines[l][lastix:])
                    ).rstrip() + "\n"

                this_source = "\n".join(diagram_source)
                hash_ = _md5(this_source)
                tag = (
                    '<div class="cs-diagram-source" diagramalign="%s">Placeholder for Diagram <code class="cs-diagram-id">%s</code></div>\n'
                    % (
                        alignment,
                        hash_,
                    )
                )
                diagrams[hash_] = this_source

                lines.insert(firstline, tag)
                ix = lastline

        ix += 1

    return "".join(lines), diagrams


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

    # parse diagrams
    text, diagram_sources = _replace_diagrams(text)

    # run through markdown
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

    import sys

    if text.startswith("<p>") and text.endswith("</p>\n"):
        text = text[3:-5]

    if diagram_sources:
        script = "\n".join(
            "catsoop.diagram_sources[%s] = %s;" % (json.dumps(k), json.dumps(v))
            for k, v in diagram_sources.items()
        )
        text = '%s<script type="text/javascript">%s</script>' % (text, script)

    return _xml_format_string(context, text) if xml else text


def _xml_format_string(context, s):
    return handle_custom_tags(context, s)


source_formats = {
    "catsoop": md_pre_handle,
    "md": md_pre_handle,
    "xml": xml_pre_handle,
    "py": py_pre_handle,
}
"""Dictionary mapping source format names to formatting handlers"""

source_format_string = {
    "catsoop": _md_format_string,
    "md": _md_format_string,
    "xml": _xml_format_string,
    "py": _xml_format_string,
}
"""Dictionary mapping source format names to formatters"""


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
                "print = myprint\n"
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
    except SystemExit as e:
        if e.code in {0, None}:
            return variables["cs___WEBOUT"].getvalue()
        elif isinstance(e.code, str):
            return e.code
        return ""
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
            code = '<pre><code class="language-python">%s</code></pre>'
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
        course_root_dir = dispatch.content_file_location(
            context, [context["cs_course"]]
        )
        course_root_dir = os.path.realpath(os.path.dirname(course_root_dir))
        b = match.groupdict()["body"]
        replacements = []
        for fname in b.splitlines():
            fname = fname.strip()
            if not fname:
                continue  # skip blank lines
            fname = os.path.join(base_dir, fname)
            fname = os.path.realpath(fname)
            if not os.path.commonpath([fname, base_dir]).startswith(course_root_dir):
                print(f"course_root_dir {course_root_dir}")
                # tried to escape the course
                msg = (
                    "<div><font color='red'><b>An &lt;include&gt; tag Error Occurred:</b></font>"
                    "<p><pre>"
                    "%s is outside the course root folder"
                    "</pre></p></div>"
                ) % (fname)
                replacements.append(msg)
                continue
            if not os.path.isfile(fname):
                msg = (
                    "<div><font color='red'><b>An &lt;include&gt; tag Error Occurred:</b></font>"
                    "<p><pre>"
                    "%s is not a file"
                    "</pre></p></div>"
                ) % (fname)
                replacements.append(msg)
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

    section = r"(catsoop-(?:chapter)|catsoop-(?:(?:sub){0,2}section))"
    section_star = r"&lt;(?P<tag>%s)\*&gt;(?P<body>.*?)&lt;/(?P=tag)\*?&gt;" % section
    section_star = re.compile(section_star, re.MULTILINE | re.DOTALL | re.IGNORECASE)

    tag_map = {
        "catsoop-section": ("h2", 1),
        "catsoop-subsection": ("h3", 2),
        "catsoop-subsubsection": ("h4", 3),
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

    for t in tree.find_all(attrs={"cs-show-if": re.compile(".*")}):
        if not eval(t.attrs["cs-show-if"], context):
            t.extract()

    for t in tree.find_all(attrs={"cs-hide-if": re.compile(".*")}):
        if eval(t.attrs["cs-hide-if"], context):
            t.extract()

    # handle <showhide>

    for i in reversed(tree.find_all("showhide")):
        i.name = "div"
        contents = i.decode_contents()
        i.clear()
        i.append(
            BeautifulSoup(source_transform_string(context, contents), "html.parser")
        )
        wrapper = tree.new_tag("div")
        wrapper["class"] = ["response"]
        i.wrap(wrapper)
        button = tree.new_tag(
            "button",
            onclick='this.setAttribute("aria-pressed", this.getAttribute("aria-pressed") === "true" ? "false" : "true");',
        )
        button["class"] = ["btn", "btn-catsoop", "showhide-toggle"]
        button.attrs["role"] = "button"
        button.attrs["aria-pressed"] = "false"
        button.string = i.attrs.get("summary", "Show/Hide")
        i.insert_before(button)

    # handle sections, etc.

    labels = {}
    textsections = [0, 0, 0]
    chapter = None
    toc_sections = []

    all_title_links = set()

    for i in tree.find_all(re.compile(section)):
        tagtype = i.name.removeprefix("catsoop-")
        if tagtype == "chapter":
            chapter = i.attrs.get("num", "0")
            tag = "h1"
            num = str(chapter)
        else:
            if tagtype == "section":
                textsections[0] += 1
                textsections[1] = 0
            elif tagtype == "subsection":
                textsections[1] += 1
                textsections[2] = 0
            elif tagtype == "subsubsection":
                textsections[2] += 1
            tag, lim = tag_map[tagtype]
            to_num = textsections[:lim]
            if chapter is not None:
                to_num.insert(0, chapter)
            num = ".".join(map(str, to_num))

        linknum = num.replace(".", "_")
        linkname = "catsoop_section_%s" % linknum
        title = i.text
        linkname_2 = _safe_title(title, all_title_links)

        lbl = i.attrs.get("label", None)
        if lbl is not None:
            labels[lbl] = {
                "type": tagtype,
                "number": num,
                "title": i.decode_contents(),
                "link": "#%s" % linkname_2,
            }
        toc_sections.append((num, linkname_2, i))
        sec = copy.copy(i)
        sec.name = tag
        sec["class"] = "cs_section_title"
        sec.insert(0, "%s) " % num)
        if lbl is not None:
            sec.attrs["id"] = "catsoop_label_%s" % lbl
        i.replace_with(sec)

        if context.get("cs_show_section_permalinks", False):
            permalink = tree.new_tag("a")
            permalink["class"] = "cs_permalink"
            permalink.attrs["href"] = "#%s" % linkname_2
            permalink.string = "§"
            sec.append(permalink)

        # references
        link = tree.new_tag("a")
        link["class"] = "anchor"
        link.attrs["name"] = linkname
        sec.insert_before(link)
        link = tree.new_tag("a")
        link["class"] = "anchor"
        link.attrs["name"] = linkname_2
        sec.insert_before(link)

    # handle refs

    for i in tree.find_all(re.compile("catsoop-ref(?:erence)?")):
        if "label" not in i.attrs:
            lbl = list(i.attrs.keys())[0]
        else:
            lbl = i.attrs["label"]

        body = i.decode_contents().strip() or '<a href="{link}">{type} {number}</a>'
        body = body.format(**labels[lbl])
        new = BeautifulSoup(body, "html.parser")
        i.replace_with(new)

    # handle table of contents

    for ix, i in enumerate(tree.find_all("tableofcontents")):
        o_toc_dom = toc_dom = tree.new_tag("ul")
        o_toc_dom.attrs["role"] = "navigation"
        o_toc_dom.attrs["aria-label"] = "Table of Contents"
        last_handled_len = 0
        for num, ref, elt in toc_sections:
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
        toc_sec.attrs["aria-hidden"] = "true"
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
        if (
            footnote_div := tree.find(id="cs_footnotes")
        ) is not None and not footnote_div.encode_contents().strip():
            fnote = '<br/>&nbsp;<hr/><b name="cs_footnotes">Footnotes</b>'
            for ix, f in enumerate(footnotes):
                ix = ix + 1
                fnote += (
                    '<p><a class="anchor" name="catsoop_footnote_%d"></a><sup style="padding-right:0.25em;color:var(--cs-base-bg-color);">%d</sup>'
                    '%s <a href="#catsoop_footnote_ref_%d">'
                    '<span class="noprint">(click to return to text)</span>'
                    "</a></p>"
                ) % (ix, ix, f, ix)
            footnote_div.append(BeautifulSoup(fnote, "html.parser"))
            if "style" in footnote_div.attrs:
                del footnote_div.attrs["style"]

    # custom URL handling in img, a, script, link

    URL_FIX_LIST = [("img", "src"), ("a", "href"), ("script", "src"), ("link", "href")]

    for tag, field in URL_FIX_LIST:
        for i in tree.find_all(tag):
            if field in i.attrs:
                i.attrs[field] = dispatch.get_real_url(context, i.attrs[field])

    # math tags
    handle_math_tags(tree)

    # code blocks: specific default behavior
    default_code_class = context.get("cs_default_code_language", "nohighlight")
    all_lines = context.get("cs_code_line_numbers", False)
    for i in tree.find_all("code"):
        if i.parent.name != "pre":
            continue

        if isinstance(i.attrs.setdefault("class", []), str):
            i.attrs["class"] = [i.attrs["class"]]

        # set default language if no language is given
        if default_code_class is not None:
            if len(i.attrs["class"]) == 0:
                i.attrs["class"] = [default_code_class]

        # add line numbers if we need to:
        classes = i.attrs["class"]
        if all_lines:
            classes.append("highlight-lines")
        else:
            for j in range(len(i.attrs["class"])):
                if classes[j].endswith("-lines") and classes[j] != "highlight-lines":
                    classes[j] = classes[j][:-6]
                    classes.append("highlight-lines")

    emoji = context.get("cs_replace_emoji", False)
    if emoji:
        from .emoji import EMOJI_MAP

        emoji_regex = re.compile(r":([a-zA-Z0-9\+\-_&.ô’Åéãíç()!#*]+?):")

        if emoji in {"external", "image"}:
            if emoji == "external":
                base_url = context.get(
                    "cs_emoji_base_url",
                    "%s/_static/_base/emoji" % context["cs_url_root"],
                )
                extension = context.get("cs_emoji_extension", "svg")
                src = lambda fname: "%s/%s.%s" % (base_url, fname, extension)
            else:

                def src(fname):
                    with open(
                        os.path.join(
                            context["cs_fs_root"],
                            "__STATIC__",
                            "emoji",
                            "%s.svg" % fname,
                        ),
                        "rb",
                    ) as f:
                        return context["csm_thirdparty"].data_uri.DataURI.make(
                            "image/svg+xml", None, True, f.read()
                        )

            def replacer(x):
                m = x.group(1)
                if m in EMOJI_MAP:
                    fname = "-".join(hex(ord(i))[2:].zfill(4) for i in EMOJI_MAP[m])
                    return (
                        '<img class="emoji" alt="%s emoji" src="%s" draggable="false" title="%s"/>'
                        % (
                            m,
                            src(fname),
                            m,
                        )
                    )
                else:
                    return x.group(0)

        elif emoji:

            def replacer(x):
                m = x.group(1)
                if m in EMOJI_MAP:
                    return '<span role="img" aria-label="%s emoji">%s</span>' % (
                        m,
                        EMOJI_MAP[m],
                    )
                else:
                    return x.group(0)

        if emoji:
            for elt in tree.find_all(text=True):
                if elt.parent.name not in {
                    "code",
                    "pre",
                    "script",
                    "[document]",
                    "head",
                } and not isinstance(elt, (Comment, Doctype)):
                    elt.replaceWith(
                        BeautifulSoup(
                            re.sub(emoji_regex, replacer, str(elt)), "html.parser"
                        )
                    )

    return str(tree).replace("</br>", "")


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
    for i in tree.find_all(re.compile("(?:display)?math")):
        i["class"] = i.get("class", [])
        try:
            if i.attrs["env"] in ["align", "align*", "eqnarray", "eqnarray*"]:
                i.string = "\\begin{aligned}%s\\end{aligned}" % i.string
            # currently ignoring other values of i.attrs["env"], namely, equation
            del i.attrs["env"]
        except KeyError:
            pass
        if i.name == "math":  # (inline math)
            i.name = "span"
        else:  # i.name == "displaymath" (display math)
            i.name = "div"
            i.attrs["style"] = "text-align:center;padding-bottom:10px;"
            i["class"].append("cs_displaymath")
        i["class"].append("cs_math_to_render")
    return tree
