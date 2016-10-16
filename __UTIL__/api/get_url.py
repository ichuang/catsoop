# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

import json

path = cs_form.get('path', None)

cs_handler = 'raw_response'
content_type = 'application/json'

try:
    path = [i for i in path.split('/') if i != '']
    cpath = list(path)
    cpath[0] = 'COURSE'
    ctx = csm_loader.spoof_early_load(path)
    out = {'ok': True, 'url': csm_dispatch.get_real_url(ctx, '/'.join(cpath))}
except:
    out = {'ok': False}

response = json.dumps(out)
