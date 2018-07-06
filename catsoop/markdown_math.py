# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
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
'''CAT-SOOP Math Mode Extension for PyMarkdown'''

from markdown.extensions import Extension
from markdown.inlinepatterns import HtmlPattern, SimpleTextPattern

_nodoc = {'Extension', 'HtmlPattern', 'SimpleTextPattern', 'absolute_import',
'unicode_literals'}

_MATH_RE = r'(^|[^\\])(\$)((?:\\\$|[^$])*)\3'
_DMATH_RE = r'(^|[^\\])(\$\$)(.*?)\3'
_ESCAPED_DOLLAR_RE = r'\\(\$)'


class RawHtmlPattern(HtmlPattern):
    """A subclass of `catsoop.thirdparty.markdown.inlinepattern.HtmlPattern`
    used to store raw inline html and return a placeholder."""

    def __init__(self, endtag, *args, **kwargs):
        self._hz_tag = endtag
        HtmlPattern.__init__(self, *args, **kwargs)

    def handleMatch(self, m):
        pre = m.group(2)
        body = self.unescape(m.group(4))
        rawhtml = '%(pre)s<%(tag)s>%(body)s</%(tag)s>' % {
            'tag': self._hz_tag,
            'body': body,
            'pre': pre
        }
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder


class MathExtension(Extension):
    """The CAT-SOOP math extension to Markdown."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns.add('dmath',
                              RawHtmlPattern('displaymath', _DMATH_RE, md),
                              '<entity')
        md.inlinePatterns.add('math',
                              RawHtmlPattern('math', _MATH_RE, md), '>dmath')
        md.inlinePatterns.add('emath',
                              SimpleTextPattern(_ESCAPED_DOLLAR_RE), '>math')
