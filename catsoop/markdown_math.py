# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE
'''CAT-SOOP Math Mode Extension for PyMarkdown'''

from __future__ import absolute_import
from __future__ import unicode_literals
from .tools.markdown.extensions import Extension
from .tools.markdown.inlinepatterns import HtmlPattern, SimpleTextPattern

_MATH_RE = r'(^|[^\\])(\$)((?:\\\$|[^$])*)\3'
_DMATH_RE = r'(^|[^\\])(\$\$)(.*?)\3'
_ESCAPED_DOLLAR_RE = r'\\(\$)'


class RawHtmlPattern(HtmlPattern):
    """Store raw inline html and return a placeholder."""
    def __init__(self, endtag, *args, **kwargs):
        self._hz_tag = endtag
        HtmlPattern.__init__(self, *args, **kwargs)

    def handleMatch(self, m):
        pre = m.group(2)
        body = self.unescape(m.group(4))
        rawhtml = '%(pre)s<%(tag)s>%(body)s</%(tag)s>' % {'tag': self._hz_tag,
                                                          'body': body,
                                                          'pre': pre}
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder


class MathExtension(Extension):
    """Add CAT-SOOP math extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns.add('dmath',
                              RawHtmlPattern('displaymath', _DMATH_RE, md),
                              '<entity')
        md.inlinePatterns.add('math',
                              RawHtmlPattern('math', _MATH_RE, md),
                              '>dmath')
        md.inlinePatterns.add('emath',
                              SimpleTextPattern(_ESCAPED_DOLLAR_RE),
                              '>math')
