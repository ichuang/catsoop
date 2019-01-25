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
SUMMARY OF THIS FILE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   The overall flow when parsing a page is:

0. Label all the <python> tags with their line number and the current file; e.g.

      <python>

   on line 67 in file "COURSE/information/content.md" becomes

      <python cs_internal_sourcefile="COURSE/information/content.md" cs_internal_linenumber=67>

½. <comment> elements are removed.

1. <include> tags are replaced by the contents of the files they reference.
   Before substitution into the current document, step 0 is run analagously on
   the contents of each file.

1½. <comment> elements are removed again.

2. <python> tags are replaced by the output of the code inside them.

   [At this point, any `post_load` events occur.]

3. `cs_transform_source : string -> string` is run on the entire page.

4a. Custom tags are handled. Each tag name in `cs_custom_tags`

      cs_custom_tags : {string => (tag_replmnt, body_replmnt, tag_replmnt, priority)}

      tag_replmt = NoneType | string | params * context -> string

      body_replmt = NoneType | string | string * params * context -> string

      params = {string => string}

   maps to a tuple of four objects. The last is an integer setting the prece-
   dence of the tag (higher numbers go first). In practice, priority should not
   make a difference. If ommitted, it is assumed to be 0. Ties are broken lexico-
   graphically.

   The remaining three objects are each either a function, string, or None.
   The first function should return the text that replaces the opening tag
   itself, and the second function should return the text that replaces the
   body of the tag, and the third function should return the text that
   replaces the closing tag. If a string is given for any of these, the
   string is used as the replacement. If None is given, no replacement is made.

   Here's an example:

      # <note>hello!</note>
      #   will become
      # <b>Note:</b> <span style="color: #808080;">hello!</span>
      #
      # <note color="#333366">sample text</note>
      #   will become
      # <b>Note:</b> <span style="color: #333366;">sample text</span>

      def note_open(params, context):
        color = params["color"] if "color" in params else "#808080"
        return '<b>Note:</b> <span style="color:%s">' % color

      cs_custom_tags = {"note": (note_open, None, "</span>")}

      # Instead of using None, we could have written
      #
      # def note_body(text, params, context):
      #     return text
      # cs_custom_tags = {"note": (note_open, note_body, "</span>")}
      #
      # and achieved the same effect.

   For each top-level custom element in the content file,

    - everything between the opening and closing tags (including the tags them-
      selves) is removed and replaced with a unique, random string ("uid").

    - The replacement opening tag and body are generated using the corresponding
      functions in `cs_custom_tags`.

    - Step 4 is recursively run on the replacement body.

    - The results are saved in the `custom_elements` dict, keyed on the uid.

4b. If the content file is in markdown, modify the source up to this point by
   calling the `md` function.

4c. Each uid in `custom_elements` is replaced by its corresponding text.

5. `cs_course_handle_custom_tags` is deprecated, but for legacy support its
   behavior is replicated here.

6. Other CAT-SOOP-specific tags are implemented using BeautifulSoup.
   If the function `cs_transform_tree : tree -> tree` is defined, it is
   called before the built-ins are applied.

7. the page source is split into the format required by __HANDLERS__ and placed
   in `cs_problem_spec`.


LIST OF BUILT-IN CUSTOM TAGS IN `cs_custom_tags`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   Name                Attributes                  Priority
   ----------------    ------------------------    --------
   comment                                            20
   question            qtype                          10



LIST OF BUILT-IN CUSTOM TAGS IMPLEMENTED WITH BEAUTIFULSOUP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   Name                Attributes
   ----------------    ------------------------
   showhide            label=...
   displaymath
   math
   tableofcontents
   chapter
   chapter*
   section
   section*
   subsection
   subsection*
   subsubsection
   subsubsection*
   ref                 label=...
   footnote

"""

import re
import os
import sys
import random
import inspect
import traceback

import copy
import hashlib

from . import tutor
from . import dispatch
from . import markdown_math
from .errors import html_format, clear_info
from io import StringIO

import markdown
from markdown.extensions import tables
from markdown.extensions import fenced_code
from markdown.extensions import sane_lists
from bs4 import BeautifulSoup

from . import debug_log

LOGGER = debug_log.LOGGER


class CatsoopSyntaxError(Exception):
    pass


class CatsoopInternalError(Exception):
    pass


# Interface Functions ----------------------------------------------------------
#   gather_page
#   assemble_page


def gather_page(context, source):
    """
    Gathers all the sources for a page.

    Parameters:
        `context` = the context of this request (should be `into` from loader.py)
        `source`    the text of this request
    Calls:
        (0) `annotate_python`
            `remove_comments`
        (1) `replace_include_tags`
            `remove_comments`
        (2) `replace_python_tags`
    Returns:
        `source`    the modified text
    """
    if context["cs_source_format"] == "py":
        exec(source, context)
        return (
            "<div style='color:red;'>"
            "<b>This is a python file.</b><br>"
            "Python files should set <tt>context['cs_problem_spec']</tt> directly."
            "</div>"
        )
    else:
        source = annotate_python(context["cs_original_path"], source)
        source = remove_comments(source)
        source = replace_include_tags(context, source)
        source = remove_comments(source)
        source = replace_python_tags(context, source)
    return source


def assemble_page(context, source, set_problem_spec=True):
    """
    Assembles the final HTML of a page.

    Parameters:
        `context`   the context of this request (should be `into` from loader.py)
        `source`    the text of this request
    Calls:
        (3) `context["cs_transform_source"]`
        (4) `replace_custom_tags`
        (5) `context["cs_course_handle_custom_tags"]`
        (6) `build_tree`
    Returns:
        `source`    the modified text
    """
    if context["cs_source_format"] == "py":
        return (
            "<div style='color:red;'>"
            "<b>This is a python file.</b><br>"
            "Python files should set <tt>context['cs_problem_spec']</tt> directly."
            "</div>"
        )

    if "cs_transform_source" in context:
        source = context["cs_transform_source"](source)

    # create `cs_custom_tags` if it does not exist
    if not "cs_custom_tags" in context:
        context["cs_custom_tags"] = {}

    # if any built-ins are missing, add them in
    for name in cs_custom_tags_builtins:
        if name not in context["cs_custom_tags"]:
            context["cs_custom_tags"][name] = cs_custom_tags_builtins[name]

    source = replace_custom_tags(context, source)

    if "cs_course_handle_custom_tags" in context:
        LOGGER.warning(
            "`cs_course_handle_custom_tags` is deprecated; use `cs_transform_source` instead."
        )
        source = context["cs_course_handle_custom_tags"](source)

    source = build_tree(source)

    if "cs_problem_spec" in context:
        LOGGER.warning("`cs_problem_spec` already exists; attempting to append.")
    else:
        context["cs_problem_spec"] = []

    if set_problem_spec:
        # split into the format required by __HANDLERS__
        if "cs_internal_qinfo" in context and len(context["cs_internal_qinfo"]) > 0:
            page = source
            for mark, question in context["cs_internal_qinfo"].items():
                p = page.split(mark)
                if len(p) == 1:
                    LOGGER.error(
                        "Question %s was not found in the page source; skipping it."
                        % mark
                    )
                if len(p) == 2:
                    context["cs_problem_spec"].append(p[0])
                    context["cs_problem_spec"].append(question)
                    page = p[1]
                else:
                    raise CatsoopInternalError("Duplicate question %s" % s)
        else:
            context["cs_problem_spec"].append(source)

    return source


# Top Level Functions ----------------------------------------------------------
#   annotate_python
#   remove_comments
#   replace_include_tags
#   replace_python_tags
#   replace_custom_tags
#   build_tree


def annotate_python(fn, source):
    """
    Modifies `<python>` tags to include two parameters:
        cs_internal_sourcefile  the name of source file that this tag is from
        cs_internal_linenumber  the line number of this tag in its source file

    Parameters:
        `fn`        the name of the original file containing the tag
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    expr = re.compile(r"< *(python|printf)( *| +[^>]+)>")

    source = source.split("\n")
    for lnum in range(len(source)):
        line = source[lnum]
        tag = expr.search(line)
        while tag is not None:
            insertion = (' cs_internal_sourcefile="%s"' % fn) + (
                ' cs_internal_linenumber="%d"' % lnum
            )
            line = line[: tag.end() - 1] + insertion + line[tag.end() - 1 :]
            pickup = tag.end() + len(insertion)
            tag = expr.search(line, pickup)
        source[lnum] = line
    return "\n".join(source)


def remove_comments(source):
    """
    Removes `<comment>` elements.

    Parameters:
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    subs_func = lambda opening, body, closing: ""
    source = replace_toplevel_element(source, "comment", subs_func)
    return source


def replace_include_tags(context, source):
    """
    Replaces `<include>` tags with the contents of the files they reference.

    Parameters:
        `context`   the context of this request
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    # handle paths relative to here unless given an absolute path
    def subs_func(opening, body, closing):
        base_dir = dispatch.content_file_location(context, context["cs_path_info"])
        base_dir = os.path.realpath(os.path.dirname(base_dir))
        replacements = []
        for fn in body.splitlines():
            fn = fn.strip()
            if not fn:
                continue  # skip blank lines
            fn = os.path.realpath(os.path.join(base_dir, fn))
            if os.path.commonprefix([fn, base_dir]) != base_dir:
                # tried to escape the course
                LOGGER.error('Unable to include "%s": outside base directory.' % fn)
                continue
            if not os.path.isfile(fn):
                LOGGER.error('Unable to include "%s": is not a file.' % fn)
                continue
            ext = os.path.splitext(fn)[1]
            if ext == ".py":
                replacements.append("<python>")
            with open(fn) as fh:
                external_source = fh.read()
                external_source = annotate_python(fn, external_source)
                replacements.append(external_source)
            if ext == ".py":
                replacements.append("</python>")
        return "\n".join(replacements)

    source = replace_toplevel_element(
        source, "include", subs_func, disallow_nesting=True
    )
    return source


def replace_python_tags(context, source):
    """
    Replaces `<python>` elements with the output of the code within, and `@{}`
    and `<printf>` with the representation of the variable they reference.

    Parameters:
        `context`   the context of this request
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    # The next 11 lines are legacy code, and
    # should probably be rewritten eventually.
    pyvar_pattern = r"[\#0\- +]*\d*(?:.\d+)?[hlL]?[diouxXeEfFgGcrs]"
    pyvar_pattern = r"(?:%%%s|%s)?" % (pyvar_pattern, pyvar_pattern)
    pyvar_pattern = r"(?P<lead>^|[^\\])@(?P<fmt>%s){(?P<body>.+?)}" % pyvar_pattern
    pyvar_regex = re.compile(pyvar_pattern, re.DOTALL | re.IGNORECASE)

    def atbrace2printf(x):
        g = x.groupdict()
        return "%s<printf %s>%s</printf>" % (
            g.get("lead", ""),
            g.get("fmt", None) or "%s",
            g["body"],
        )

    # substitution function for `python` and `printf` tags
    def subs_func(opening, body, closing):
        name, params = parse_tag(opening)

        if "cs_internal_linenumber" not in params:
            emergency = 10000
            LOGGER.warning(
                "Python tag %s has unknown position; starting line numbering at %d."
                % emergency
            )
            params["cs_internal_linenumber"] = emergency
        if "cs_internal_sourcefile" not in params:
            LOGGER.warning("Python tag %s has unknown source." % opening)
            params["cs_internal_sourcefile"] = "UNKNOWN"

        linenumber = int(params["cs_internal_linenumber"])
        sourcefile = params["cs_internal_sourcefile"]

        if name == "printf":
            keys = list(params.keys())
            recognized_params = ["cs_internal_linenumber", "cs_internal_sourcefile"]
            for p in recognized_params:
                if p in keys:
                    keys.remove(p)
            if len(keys) > 1:
                raise CatsoopSyntaxError(
                    "Improper tag %s: `printf` only admits one attribute" % opening
                )
            elif len(keys) == 1:
                if params[keys[0]] is not None:
                    raise CatsoopSyntaxError(
                        'Improper tag %s: `printf` formatting attribute does not use "name=value" syntax'
                        % opening
                    )
                fmt = params[keys[0]]
            else:
                fmt = "%s"

            body = "print(%r %% (%s,))" % (fmt, body)

        if "show" in params:
            if params["show"] is not None:
                raise CatsoopSyntaxError(
                    "Improper tag %s: `show` does not take any values" % opening
                )
            code = '<pre><code class="lang-python">%s</code></pre>'
            out = code % html_format(body)
        else:
            out = ""

        if "norun" in params:
            if params["norun"] is not None:
                raise CatsoopSyntaxError(
                    "Improper tag %s: `norun` does not take any values" % opening
                )
            return out.strip()

        if "noresult" in params:
            if params["noresult"] is not None:
                raise CatsoopSyntaxError(
                    "Improper tag %s: `noresult` does not take any values" % opening
                )
            display_result = False
        else:
            display_result = True

        if "env" in params:
            envname = params["env"]
            if envname not in context["cs__python_envs"]:
                context["cs__python_envs"][envname] = {}
            execution_context = context["cs__python_envs"][envname]
        else:
            execution_context = context

        result = execute_python(
            context, body, execution_context, linenumber, sourcefile
        )
        return (out + result).strip() if display_result else out.strip()

    if "cs__python_envs" not in context:
        context["cs__python_envs"] = {}

    # convert @{...} notation into <printf>...</printf>
    source = re.sub(pyvar_regex, atbrace2printf, source)

    # evaluate <python> and <printf> tags
    source = replace_toplevel_element(
        source, ["python", "printf"], subs_func, disallow_nesting=True
    )
    source = source.replace(r"\@{", "@{")
    return source


def replace_custom_tags(context, source):
    """
    Replaces custom tags as described at the top of this file (language.py).

    Unlike `replace_include_tags`, `replace_python_tags`, and `build_tree`, this
    function should not modify `context`. The argument `source` is passed in as
    a separate argument to reflect this difference in paradigm.

    Parameters:
        `context`   the context of this request
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    custom_tags = context["cs_custom_tags"]
    names_todo = list(custom_tags.keys())

    for name, defs in custom_tags.items():
        if not isinstance(defs, tuple):
            LOGGER.error(
                "Invalid definition of %s in `cs_custom_tags`: must map to tuple. Skipping it."
                % name
            )
            names_todo.remove(name)
        elif len(defs) < 3:
            LOGGER.error(
                "Invalid definition of %s in `cs_custom_tags`: underspecified. Skipping it."
                % name
            )
            names_todo.remove(name)
        elif len(defs) < 4:
            context["cs_custom_tags"][name] = defs + (0,)
        elif not isinstance(defs[3], int):
            LOGGER.error(
                "Invalid definition of %s in `cs_custom_tags`: precedence must be an integer. Skipping it."
                % name
            )
            names_todo.remove(name)

    # Since timsort is stable, we
    # sort lexicographically...
    names_todo.sort()
    # ...then sort by precedence,
    names_todo.sort(key=lambda n: custom_tags[n][3])
    # and put biggest first
    names_todo.reverse()

    symbols = {}
    for name in names_todo:
        open_replmnt, body_replmnt, close_replmnt, priority = custom_tags[name]

        def subs_func(opening, body, closing, context):
            _, params = parse_tag(opening)

            if open_replmnt is None:
                new_open = opening
            elif isinstance(open_replmnt, str):
                new_open = open_replmnt
            else:
                new_open = open_replmnt(params, context)

            if body_replmnt is None:
                new_body = body
            elif isinstance(body_replmnt, str):
                new_body = body_replmnt
            else:
                new_body = body_replmnt(body, params, context)

            if close_replmnt is None:
                new_close = closing
            elif isinstance(close_replmnt, str):
                new_close = close_replmnt
            else:
                new_close = close_replmnt(params, context)

            new_body = replace_custom_tags(new_body, context)

            return new_open + new_body + new_close

        source = replace_toplevel_element(
            source, name, subs_func, symbols=symbols, context=context
        )

    if context["cs_source_format"] == "md":
        source = markdown.markdown(
            source,
            extensions=[
                tables.TableExtension(),
                fenced_code.FencedCodeExtension(),
                sane_lists.SaneListExtension(),
                markdown_math.MathExtension(),
            ],
        )

    for sym, repl in symbols.items():
        source = source.replace(sym, repl)

    return source


def build_tree(context, source):
    """
    Create a BeautifulSoup tree and implement the functionality of the remainder
    of the custom tags.

    Parameters:
        `context`   the context of this request
        `source`    the text of this request
    Returns:
        `source`    the modified text
    """
    tree = BeautifulSoup(source, "html.parser")

    if "cs_transform_tree" in context:
        tree = context["cs_transform_tree"](tree)

    return legacy_tree(context, tree)


# Helper Functions -------------------------------------------------------------
#   replace_toplevel_elements
#   parse_tag
#   execute_python


def replace_toplevel_element(
    source, name, substitution, disallow_nesting=False, symbols=None, context=None
):

    # We'd like to ensure that tags are balanced and then perform some substitu-
    # tion on top-level elements. BeautifulSoup would be just the tool for this,
    # but the HTML parser we use with bs4 amends the tree to make it well-formed
    # (which we don't want to happen yet). Using a different parser could poten-
    # tially work, and perhaps in the future we'll do that instead.

    # Note that in some cases (when elements interleave), there is a difference
    # between, e.g.,
    #   source = replace_toplevel_element(source, a, subs_func)
    #   source = replace_toplevel_element(source, b, subs_func)
    # and
    #   source = replace_toplevel_element(source, [a, b], subs_func)

    # To do: allow the ">" character to appear in quoted strings within a tag

    generate_symbols = symbols is not None

    if generate_symbols:
        if context is None:
            context = {}

        if "cs_internal_symbol_counter" not in context:
            context["cs_internal_symbol_counter"] = 0

    if isinstance(name, list):
        name = "(" + "|".join(re.escape(n) for n in name) + ")"
    else:
        name = "(" + re.escape(name) + ")"

    opening_expr = re.compile(r"< *%s( *| +[^>]+)>" % name)
    closing_expr = re.compile(r"</ *%s *>" % name)
    # find all opening and closing tags
    opening_tags = [(m, m.group(1), True) for m in re.finditer(opening_expr, source)]
    closing_tags = [(m, m.group(1), False) for m in re.finditer(closing_expr, source)]
    tags = sorted(opening_tags + closing_tags, key=(lambda t: t[0].start()))

    while len(tags) > 0:
        # check for an unexpected closing tag
        if not tags[0][2]:
            raise CatsoopSyntaxError("Unexpected closing tag %s" % tags[0][0].group(0))
        # find paired tag
        pre_start = tags[0][0].start()
        start = tags[0][0].end()
        stack = []
        for t in tags:
            if t[2]:  # opening tag
                stack.append(t)
            else:  # closing tag
                previous = stack.pop()
                if previous[1] != t[1]:
                    raise CatsoopSyntaxError(
                        "Unexpected closing tag %s" % t[0].group(0)
                    )
            if disallow_nesting and len(stack) > 1:
                raise CatsoopSyntaxError("Nested tag %s" % t[0].group(0))
            if len(stack) == 0:
                stop = t[0].start()
                post_stop = t[0].end()
                break
        # check for an unmatched opening tag
        if len(stack) != 0:
            raise CatsoopSyntaxError("Unmatched opening tag %s" % tags[0][0].group(0))

        before = source[:pre_start]
        opening = source[pre_start:start]
        body = source[start:stop]
        closing = source[stop:post_stop]
        after = source[post_stop:]

        if len(inspect.getfullargspec(substitution).args) == 4:
            inner = substitution(opening, body, closing, context)
        else:
            inner = substitution(opening, body, closing)

        if generate_symbols:
            replacement = "⟨CATSOOP:SYMBOL:%d:%06X⟩" % (
                context["cs_internal_symbol_counter"],
                random.randint(0, 2 ** 24 - 1),
            )
            context["cs_internal_symbol_counter"] += 1
            symbols[replacement] = inner
        else:
            replacement = inner

        source = before + replacement + after
        len_change = len(replacement) - (len(opening) + len(body) + len(closing))
        pickup = post_stop + len_change

        # rather than try to manually keep track of the matches' indices as
        # the text is changed, simply re-match (this is much less efficient,
        # but means that the match data will be correct without adjustment)
        opening_tags = [
            (m, m.group(1), True) for m in opening_expr.finditer(source, pickup)
        ]
        closing_tags = [
            (m, m.group(1), False) for m in closing_expr.finditer(source, pickup)
        ]
        tags = sorted(opening_tags + closing_tags, key=(lambda t: t[0].start()))

    return source


def parse_tag(tag):
    """
    Railroad diagram for the syntax of a tag

                             /<----------+---------------------------------------------------\
                            /             \                                                   \
    `<` -> WS* -> name -> WS -> parameter -+-> WS* -> `=` -> WS* -> value ---------------------+-> WS* -> `>`
                       \                                         \                            /
                        \-> `>`                                   \---> `"` -> .* -> `"` --->/
                                                                   \                        /
                                                                    \-> `'` -> .* -> `'` ->/
    WS = whitespace, * = Kleene star,
    . = any character besides relevant delimiter
    """
    # Note that this allows for strange things, like
    #   <example opt=ion=s>
    # producing
    #   ("example", {"opt": "ion=s"})
    #
    # The upside is that the rules are simple and
    # there's only one way to produce an error.

    # To do: add support for backslash escape

    original_tag = tag
    params = {}

    # we know the first character is `<`
    tag = tag[1:].lstrip()

    # grab until whitespace or `>` to get the name
    m = re.compile(r"[ >]").search(tag)
    name = tag[: m.start()]
    tag = tag[m.start() :].lstrip()

    # this could just be `while True`, but those always make me nervous
    while len(tag) > 0:
        if tag[0] == ">":
            break

        # grab until whitespace or `>` or `=` to get a parameter
        m = re.compile(r"[ >=]").search(tag)
        p = tag[: m.start()]
        tag = tag[m.start() :].lstrip()

        # case 1: parameter has a value
        if tag[0] == "=":
            tag = tag[1:].lstrip()

            if tag[0] == "'":
                tag = tag[1:]
                m = re.compile(r"'").search(tag)
                if m is None:
                    raise CatsoopSyntaxError(
                        "Improper tag %s: missing delimiter" % original_tag
                    )
                params[p] = tag[: m.start()]
                tag = tag[m.start() + 1 :].lstrip()

            elif tag[0] == '"':
                tag = tag[1:]
                m = re.compile(r'"').search(tag)
                if m is None:
                    raise CatsoopSyntaxError(
                        "Improper tag %s: missing delimiter" % original_tag
                    )
                params[p] = tag[: m.start()]
                tag = tag[m.start() + 1 :].lstrip()

            else:
                m = re.compile(r"[ >]").search(tag)
                params[p] = tag[: m.start()]
                tag = tag[m.start() :].lstrip()

        # case 2: parameter does NOT have a value
        else:
            params[p] = None

    return (name, params)


def execute_python(context, body, variables, offset, sourcefile):
    """
    Evalutes code in a given environment, and returns its output (if any).

    Makes use of a special variable `cs___WEBOUT`, which is a file-like object.
    Any data written to `cs___WEBOUT` will be returned. Overwrites `print` in
    the given environment so that its output is directed to `cs___WEBOUT`
    instead of STDOUT.

    Parameters:
        `context`       the context of this request
        `body`          the string representation of python code to be executed
        `variables`     the dictionary representation of the environment in
                          which the code should be executed
        `offset`        the adjustment that should be made to line numbering
        `sourcefile`    the name of the file from which this code was taken
    Returns:
        `result`        string containing anything written to `cs___WEBOUT`
    """
    variables.update({"cs___WEBOUT": StringIO()})
    try:
        body = remove_common_leading_whitespace(body)
        if isinstance(body, int):
            return (
                "<div style='color:red;'>"
                "<b>A Python Error Occurred:</b>"
                "<p><pre>"
                "Inconsistent indentation on line %d of python tag (line %d of file %s)"
                "</pre></p>"
                "</div>"
            ) % (body, body + offset, sourcefile)
        body = indent_python(body)
        body = (
            (
                "_cs_stdout_print = print\n"
                "def _cs_web_print(*args, **kwargs):\n"
                '    if "file" not in kwargs:\n'
                '        kwargs["file"] = cs___WEBOUT\n'
                "    _cs_stdout_print(*args, **kwargs)\n"
                "print = cs_print = _cs_web_print\n"
                "try:\n"
            )
            + code
            + (
                "\nexcept Exception as e:\n"
                "    raise e\n"
                "finally:\n"
                "    print = _cs_stdout_print"
            )
        )
        body = body.replace("tutor.init_random()", "tutor.init_random(globals())")
        body = body.replace("tutor.question(", "tutor.question(globals(),")
        exec(body, variables)
        return variables["cs___WEBOUT"].getvalue()

    except:
        exc = sys.exc_info()
        tb_entries = traceback.extract_tb(exc[2])
        tb_fname, tb_line, tb_func, tb_text = tb_entries[-1]
        exc_only = traceback.format_exception_only(exc[0], exc[1])

        if exc[0] == SyntaxError:
            text = "Syntax error in python tag (line %d of file %s):\n" % (
                tb_line - 8,
                tb_line + offset - 8,
                sourcefile,
            )

            def replace_line_number(m):
                return "line %d" % (int(m.group(1)) - 8)

            exc_only = [re.sub(r"line (\d+)", replace_line_number, i) for i in exc_only]

        elif tb_func == "<module>":
            text = (
                "Error on line %d of python tag (line %d of file %s):\n    %s\n\n"
                % (
                    tb_line - 8,
                    tb_line + offset - 8,
                    sourcefile,
                    body.splitlines()[tb_line - 1].strip(),
                )
            )
        else:
            text = context["csm_errors"].error_message_content(context, html=False)
            exc_only = [""]

        text = "".join([text] + exc_only)

        err = html_format(clear_info(context, text))
        ret = (
            "<div style='color:red;'>"
            "<b>A Python Error Occurred:</b>"
            "<p><pre>%s</pre></p>"
            "</div>"
        ) % err
        return ret


# Built-in Custom Tags ---------------------------------------------------------
#  build_question
#  cs_custom_tags_builtins

___valid_qname = re.compile(r"^[_A-Za-z][_A-Za-z0-9]*$")


def ___reformat_tag(name, params):
    return (
        "<"
        + name.strip
        + " ".join((a if v is None else a + "=" + "...") for a, v in params.items())
        + ">"
    )


def build_question(body, params, context):
    if "cs_internal_qcount" not in context:
        context["cs_internal_qcount"] = 0

    if "cs_internal_qinfo" not in context:
        context["cs_internal_qinfo"] = {}

    if "cs_problem_spec" not in context:
        context["cs_problem_spec"] = []

    if len(params) != 1:
        raise CatsoopSyntaxError(
            "Improper tag %s: `question` takes exactly one attribute"
            % ___reformat_tag("question", params)
        )

    qtype = list(params.keys())[0]

    if params[qtype] is not None:
        raise CatsoopSyntaxError(
            "Improper tag %s: qtype does not take any values"
            % ___reformat_tag("question", params)
        )

    out = []
    env = dict(context)
    try:
        code = remove_common_leading_whitespace(body)
        if isinstance(code, int):
            return (
                "<div style='color:red;'>"
                "<b>A Python Error Occurred:</b>"
                "<p><pre>"
                "Inconsistent indentation on line %d of question tag"
                "</pre></p>"
                "</div>"
            ) % code

        exec(code, env)

        if "csq_name" not in env:
            env["csq_name"] = "q%06d" % context["cs_internal_qcount"]
            context["cs_internal_qcount"] += 1

        if ___valid_qname.match(env["csq_name"]):
            replacement = "⟨CATSOOP:QUESTION:%s:%06X⟩" % (
                env["csq_name"],
                random.randint(0, 2 ** 24 - 1),
            )
            if qtype != "dummy":
                context["cs_internal_qinfo"][replacement] = tutor.question(
                    context, qtype, **env
                )
            return replacement

        else:
            return (
                "<div class='question' style='color:red;'>"
                "ERROR: Invalid question name <code>%r</code>"
                "</div>"
            ) % env["csq_name"]
    except:
        exc = sys.exc_info()
        tb_entries = traceback.extract_tb(exc[2])
        tb_fname, tb_line, tb_func, tb_text = tb_entries[-1]
        exc_only = traceback.format_exception_only(exc[0], exc[1])
        if exc[0] == SyntaxError:
            text = "Syntax error in question tag:\n"
        elif tb_func == "<module>":
            text = "Error on line %d of question tag." % tb_line
            try:
                text += "\n    %s\n\n" % code.splitlines()[tb_line - 1].strip()
            except:
                pass
        else:
            text = context["csm_errors"].error_message_content(context, html=false)
            exc_only = [""]
        text = "".join([text] + exc_only)
        err = html_format(clear_info(context, text))
        ret = (
            "<div style='color:red;'>"
            "<b>A Python Error Occurred:</b>"
            "<p><pre>%s</pre></p>"
            "</div>"
        ) % err
        return ret


cs_custom_tags_builtins = {
    "comment": ("", "", "", 20),
    "question": ("", build_question, "", 15),
    "pre": (None, None, None, 14),  # These definitions leave the
    "displaymath": (None, None, None, 13),  # tags unchanged, but they'll
    "math": (None, None, None, 12),  # still get turned into symbols
    "script": (None, None, None, 11),  # so that markdown doesnt' break
    "chapter": ("<h1>", None, "</h1>", 9),
    "section*": ("<h2>", None, "</h2>", 8),
    "subsection*": ("<h3>", None, "</h3>", 7),
    "subsubsection*": ("<h4>", None, "</h4>", 6),
}

# Legacy Functions -------------------------------------------------------------
#   None of these were re-written for CAT-SOOP v14

___indent_regex = re.compile(r"^(\s*)")

___string_regex = re.compile(
    r"""(\"\"\"[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*\"\"\"|'''[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''|'[^\n'\\]*(?:\\.[^\n'\\]*)*'|"[^\n"\\]*(?:\\.[^\n"\\]*)*")""",
    re.MULTILINE | re.DOTALL,
)

___ascii_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def ___tab_replacer(x):
    return x.group(1).replace("\t", "    ")


def ___replace_indentation_tabs(x):
    return re.sub(___indent_regex, ___tab_replacer, x)


def remove_common_leading_whitespace(x):
    lines = x.splitlines()
    if len(lines) == 0:
        return ""
    for ix in range(len(lines)):
        if lines[ix].strip():
            break
    first_ix = ix
    candidate = re.match(___indent_regex, lines[first_ix])
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


def indent_python(c):
    strings = {}
    # start by removing strings and replacing them with unique character sequences
    def replacer(x):
        new_id = None
        while new_id is None or new_id in strings or new_id in c:
            new_id = "".join(random.choice(ascii_letters) for i in range(20))
        strings[new_id] = x.group(1)
        return new_id

    c = re.sub(___string_regex, replacer, c)
    # now that strings are out of the way, change the indentation of every line
    c = "\n".join("    %s" % ___replace_indentation_tabs(i) for i in c.splitlines())
    c = "    pass\n%s" % c
    # finally, reintroduce strings
    for k, v in strings.items():
        c = c.replace(k, v)
    return c


def legacy_tree(context, tree):
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
