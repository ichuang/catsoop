# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE


def handle(context):
    content = context['response']
    typ = context.get('content_type', 'text/plain')
    headers = {'Content-type': typ, 'Content-length': str(len(content))}
    return ('200', 'OK'), headers, content
