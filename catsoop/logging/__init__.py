# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the Soopycat License, version 1.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the Soopycat License for more details.

# You should have received a copy of the Soopycat License along with this
# program.  If not, see <https://smatz.net/soopycat>.

from . import sqlite
from . import catsoopdb

_db_type_map = {
    'catsoopdb': catsoopdb,
    'sqlite': sqlite,
}

def get_logger(context):
    db_type = context.get('cs_log_type', 'catsoopdb')
    logging_module = _db_type_map.get(db_type, None)
    if logging_module is None:
        raise NameError('No such logger: %s' % db_type)
    return logging_module
