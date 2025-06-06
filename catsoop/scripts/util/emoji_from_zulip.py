import os
import ast
import pprint
import subprocess
import urllib.request

ZULIP_EMOJI_CODE_URL = "https://raw.githubusercontent.com/zulip/zulip/master/tools/setup/emoji/emoji_names.py"

emoji_text = urllib.request.urlopen(ZULIP_EMOJI_CODE_URL).read().decode("utf-8")
emoji_text = "{%s}" % emoji_text.split("{", 1)[1].rsplit("}", 1)[0]

EMOJI_NAME_MAPS = ast.literal_eval(emoji_text)

emoji_map = {
    "slight_smile": "🙂",
    "water_wave": "🌊",
}

for k, v in EMOJI_NAME_MAPS.items():
    codepoints = k.split("-")
    emoji_map[v["canonical_name"]] = "".join(chr(int(i, 16)) for i in codepoints)

for k, v in EMOJI_NAME_MAPS.items():
    codepoints = k.split("-")
    for a in v["aliases"]:
        if a not in emoji_map:
            emoji_map[a] = "".join(chr(int(i, 16)) for i in codepoints)

TOP_TEXT = '''# -*- coding: utf-8 -*-
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
"""
Mapping from emoji names to unicode code points

Auto-generated from a mapping from [Zulip](https://github.com/zulip/zulip).
"""
'''

d = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
fname = os.path.join(d, "emoji.py")
with open(fname, "w") as f:
    f.write(TOP_TEXT)
    f.write("\n")
    f.write("EMOJI_MAP = ")
    f.write(pprint.pformat(emoji_map))

subprocess.check_output(["black", fname])
