# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

# WSGI Interface to CAT-SOOP

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import catsoop.dispatch as dispatch


def application(environ, start_response):
    """
    WSGI application interface for CAT-SOOP, as specified in PEP
    3333 (http://www.python.org/dev/peps/pep-3333/).
    """
    status, headers, content = dispatch.main(environ)
    start_response('%s %s' % (status[0], status[1]), headers.items())
    if isinstance(content, str):
        return [content]
    else:
        return content
