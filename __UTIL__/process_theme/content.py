# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/agpl-3.0-standalone.html>.

ctx = {}
csm_loader.load_global_data(ctx)

preload_from = cs_form.get('preload', '')
if preload_from != '':
    opath = path = [i for i in preload_from.split('/') if i != '']
    course = path[0]
    ctx['cs_course'] = course
    path = path[1:]
    cfile = csm_dispatch.content_file_location(ctx, opath)
    csm_loader.do_early_load(ctx, course, path, ctx, cfile)

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
