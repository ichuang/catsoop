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

import colorsys

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

def _hex(n):
    n = int(n)
    return hex(n)[2:4]

def _rgb_to_hex(tup):
    return '#%s%s%s' % tuple(map(_hex, tup))

def _rgb_to_hsv(tup):
    return colorsys.rgb_to_hsv(*(i/255 for i in tup))

def _hsv_to_rgb(tup):
    return tuple(int(i*255) for i in colorsys.hsv_to_rgb(*tup))

ctx['_hex_to_rgb'] = _hex_to_rgb
ctx['_rgb_to_hex'] = _rgb_to_hex
ctx['_rgb_to_hsv'] = _rgb_to_hsv
ctx['_hsv_to_rgb'] = _hsv_to_rgb

preload_from = cs_form.get('preload', '')
if preload_from != '':
    path = [i for i in preload_from.split('/') if i != '']
    ctx['cs_path_info'] = []
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
