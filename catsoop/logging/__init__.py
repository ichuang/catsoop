# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

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
