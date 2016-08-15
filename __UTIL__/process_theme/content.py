# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

ctx = {}
csm_loader.load_global_data(ctx)


def _hex_to_rgb(x):
    if x.startswith('#'):
        return _hex_to_rgb(x[1:])
    if len(x) == 3:
        return _hex_to_rgb(''.join(i*2 for i in x))
    try:
        return tuple(int(x[i*2:i*2+2], 16) for i in range(3))
    except:
        return (0, 0, 0)

ctx['_hex_to_rgb'] = _hex_to_rgb

preload_from = cs_form.get('preload', '')
if preload_from != '':
    path = [i for i in preload_from.split('/') if i != '']
    ctx.update(csm_loader.spoof_early_load(path))

original_loc = cs_form.get('theme', 'BASE/themes/base.css')
temp = csm_dispatch._real_url_helper(ctx, original_loc)
if '__STATIC__' not in temp:
    temp = csm_dispatch._real_url_helper(ctx, 'BASE/themes/base.css')
original_loc = csm_dispatch.static_file_location(ctx, temp[2:])
with open(original_loc) as f:
    original_content = f.read()


cs_handler = 'raw_response'
content_type = 'text/css'

response = csm_language.handle_python_tags(ctx, original_content)
