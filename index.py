#!/usr/bin/env python3

# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

# index.py
# This file is the main CGI interface to CAT-SOOP

import os
import sys
import cgi
import cgitb
import platform

import catsoop.web as web

cgitb.enable()

if platform.system() == 'Windows':
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def write(x):
    sys.stdout.write(x)
    sys.stdout.flush()


if __name__ == '__main__':
    headers, content = web.render(web.get_page_content(os.environ))
    write(headers)
    if isinstance(content, str):
        write(content)
    else:
        for i in content:
            write(i)
