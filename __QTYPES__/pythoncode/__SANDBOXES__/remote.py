# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

import json
import urllib
import urllib2

SANDBOX_URL = 'https://cat-soop.org/python3-sandbox.py'


def run_code(context, code, options):
    code = code.replace('\r\n', '\n')
    data = urllib.urlencode({"code": code, "options": options})
    request = urllib2.Request(
        context.get('csq_sandbox_url', SANDBOX_URL), data)
    try:
        resp = urllib2.urlopen(request, data).read()
        resp = json.loads(resp)
        out = resp['stdout']
        err = resp['stderr']
        fname = resp['filename']
    except:
        out = ''
        err = ''
        fname = ''
    return fname, out, err
