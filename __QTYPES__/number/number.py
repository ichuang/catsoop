# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 2.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

tutor.qtype_inherit("expression")

defaults['csq_render_result'] = False

def _input_check(src, tree):
    if tree[0] == 'NUMBER':
        return None
    if tree[0] == '/' and tree[1][0] == 'NUMBER' and tree[2][0] == 'NUMBER':
        return None
    return 'Your input must be a single number or simple fraction.'

defaults['csq_input_check'] = _input_check
