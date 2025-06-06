# This file is part of CAT-SOOP
# Copyright (c) 2011-2025 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
"""CAT-SOOP Extensions for [Mistletoe](https://github.com/miyuchina/mistletoe)"""

import re
import html

from mistletoe import Document
from mistletoe.span_token import SpanToken, tokenize_inner
from mistletoe.block_token import BlockToken, tokenize
from mistletoe.html_renderer import HTMLRenderer

# Syntax Highlighting for Code Spans

# auto-generated list of languages for syntax highlighting, from highlight.js
LANGS = [
    "apache",
    "apacheconf",
    "bash",
    "sh",
    "zsh",
    "c",
    "c",
    "h",
    "coffeescript",
    "coffee",
    "cson",
    "iced",
    "cpp",
    "cc",
    "c\\+\\+",
    "h\\+\\+",
    "hpp",
    "hh",
    "hxx",
    "cxx",
    "csharp",
    "cs",
    "c#",
    "css",
    "diff",
    "patch",
    "go",
    "golang",
    "http",
    "https",
    "ini",
    "toml",
    "java",
    "jsp",
    "javascript",
    "js",
    "jsx",
    "mjs",
    "cjs",
    "json",
    "kotlin",
    "kt",
    "less",
    "lua",
    "makefile",
    "mk",
    "mak",
    "xml",
    "html",
    "xhtml",
    "rss",
    "atom",
    "xjb",
    "xsd",
    "xsl",
    "plist",
    "wsf",
    "svg",
    "markdown",
    "md",
    "mkdown",
    "mkd",
    "nginx",
    "nginxconf",
    "objectivec",
    "mm",
    "objc",
    "obj-c",
    "perl",
    "pl",
    "pm",
    "php",
    "php",
    "php3",
    "php4",
    "php5",
    "php6",
    "php7",
    "php-template",
    "plaintext",
    "text",
    "txt",
    "properties",
    "python",
    "py",
    "gyp",
    "ipython",
    "python-repl",
    "pycon",
    "ruby",
    "rb",
    "gemspec",
    "podspec",
    "thor",
    "irb",
    "rust",
    "rs",
    "scss",
    "shell",
    "console",
    "sql",
    "swift",
    "typescript",
    "ts",
    "yaml",
    "yml",
    "YAML",
]


class SyntaxHighlightedCodeSpan(SpanToken):
    pattern = re.compile(
        r"(?P<lang>(?:%s)?)(?P<open>`+)(?P<body>.*?)(?P=open)" % "|".join(LANGS),
        re.DOTALL,
    )
    parse_inner = False
    precedence = SpanToken.precedence + 2

    def __init__(self, match):
        self.language = match.group("lang").strip()
        self.body = match.group("body")


# Math

_nodoc = {
    "Document",
    "SpanToken",
    "tokenize_inner",
    "BlockToken",
    "tokenize",
    "HTMLRenderer",
}


class Math(SpanToken):
    """
    Mistletoe extension for handling inline math (`$...$`)
    """

    pattern = re.compile(r"(?:^|(?<!\\))\$(?P<body>(?:\\\$|[^$])*)\$")
    parse_inner = False

    def __init__(self, match):
        self.body = match.group("body")


class DisplayMath(SpanToken):
    """
    Mistletoe extension for handling display math (`$$...$$`)
    """

    pattern = re.compile(r"\$\$(?P<body>.*?)\$\$", re.MULTILINE | re.DOTALL)
    parse_inner = False
    precedence = SpanToken.precedence + 2

    def __init__(self, match):
        self.body = match.group("body")


class DisplayMathEnv(SpanToken):
    """
    Mistletoe extension for handling various math environments, e.g.
    `\\begin{equation}...\\end{equation}`
    """

    pattern = re.compile(
        r"\\begin\s*{(?P<env>(?:equation|eqnarray|align)\*?)}(?P<body>.*?)\\end\s*{(?P=env)}",
        re.MULTILINE | re.DOTALL,
    )
    parse_inner = False
    precedence = SpanToken.precedence + 1

    def __init__(self, match):
        self.body = match.group("body")
        self.env = match.group("env")


class EscapedDollar(SpanToken):
    """
    Mistletoe extension for handling escaped dollar signs (`\\$`)
    """

    pattern = re.compile(r"(?<!\\)\\(\$)")


# Callouts


class Callout(BlockToken):
    """
    Mistletoe extension for handling "callout" dialog boxes
    """

    classes = ["note", "tip", "info", "warning", "error"]
    start_regex = re.compile(r"!!!(?P<header>.*)")

    def __init__(self, match):
        self.type, title, raw_lines = match
        self.title = tokenize([title])
        self.children = tokenize(raw_lines)

    @classmethod
    def start(cls, line):
        match = cls.start_regex.match(line)
        if not match:
            return False

        cls.indent = None

        header = (match.group("header") or "").strip()
        try:
            type_, title = header.split(":", 1)
            if type_.lower() not in cls.classes:
                type_ = "note"
                title = header
        except ValueError:
            if header.lower() in cls.classes:
                type_ = header
                title = ""
            else:
                type_ = "note"
                title = header.strip()

        cls.type, cls.title = type_.lower(), title
        return True

    @classmethod
    def read(cls, lines):
        out_lines = []
        next(lines)  # consume the starting line (with !!!)
        line = lines.peek()
        while line is not None:
            if cls.indent is None:
                try:
                    cls.indent = re.match(r"^\s*", line).group(0)
                except AttributeError:
                    # None as return type from match?  no indent, move on
                    break

            # if there is no indent on the following line, break here
            if not cls.indent:
                break

            if line.strip():
                # nonempty line.
                if not line.startswith(cls.indent):
                    break
                else:
                    out_lines.append(line[len(cls.indent) :])
            else:
                out_lines.append(line)

            # move on to the next line
            next(lines)
            line = lines.peek()

        return cls.type, cls.title, out_lines


class CatsoopRenderer(HTMLRenderer):
    """
    Mistletoe renderer incorporating the various extensions
    """

    def __init__(self):
        HTMLRenderer.__init__(
            self,
            Callout,
            DisplayMathEnv,
            DisplayMath,
            Math,
            EscapedDollar,
            SyntaxHighlightedCodeSpan,
        )

    def render_syntax_highlighted_code_span(self, token):
        if token.language:
            return '<span class="hl"><code class="lang-%s">%s</code></span>' % (
                token.language,
                html.escape(token.body),
            )
        return "<code>%s</code>" % html.escape(token.body)

    def render_math(self, token):
        return f"<math>{token.body}</math>"

    def render_display_math(self, token):
        return f"<displaymath>{token.body}</displaymath>"

    def render_display_math_env(self, token):
        return f'<displaymath env="{token.env}">{token.body}</displaymath>'

    def render_callout(self, token):
        if token.title:
            rendered_title = '<div class="callout-title">%s</div>' % "".join(
                self.render_inner(i) for i in token.title
            )
        else:
            rendered_title = ""
        rendered_body = "".join(self.render(i) for i in token.children)
        return f'<div class="callout callout-{token.type}">{rendered_title}\n\n{rendered_body}\n</div>'

    def render_escaped_dollar(self, token):
        return "$"


def markdown(x):
    """
    Main entrypoint, takes in a Markdown-formatted string, parses it using
    Mistletoe (with the extensions above loaded in), and returns an HTML-string
    as a result.
    """
    with CatsoopRenderer() as renderer:
        return renderer.render(Document(x))
