# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json

if 'source' in cs_form:
    try:
        sources = json.loads(cs_form['source'])
    except:
        sources = [cs_form['source']]
else:
    sources = []

cs_handler = 'raw_response'
content_type = 'application/json'

lang = csm_language
soup = csm_tools.bs4.BeautifulSoup

response = [csm_language._md_format_string(globals(), i, False) for i in sources]
response = json.dumps([str(lang.handle_math_tags(soup(i, 'html.parser')))
                       for ix, i in enumerate(response)])
