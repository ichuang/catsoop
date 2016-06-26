# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

import sys
import time
import shutil
import signal
import hashlib
import resource
import threading
import subprocess

_resource_mapper = {
    'CPUTIME': (resource.RLIMIT_CPU, lambda x: (x, x + 1)),
    'MEMORY': (resource.RLIMIT_AS, lambda x: (x, x)),
    'FILESIZE': (resource.RLIMIT_FSIZE, lambda x: (x, x)),
}


class PKiller(threading.Thread):
    def __init__(self, proc, timeout):
        threading.Thread.__init__(self)
        self.proc = proc
        self.timeout = timeout

    def run(self):
        end = time.time() + self.timeout
        while (time.time() < end):
            time.sleep(0.1)
            if self.proc.poll() is not None:
                return
        if self.proc.poll() is not None:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)


def run_code(context, code, options):
    rlimits = [(resource.RLIMIT_NPROC, (0, 0))]
    for key, val in _resource_mapper.iteritems():
        if key == 'MEMORY' and options[key] <= 0:
            continue
        rlimits.append((val[0], val[1](options[key])))

    def limiter():
        os.setsid()
        for i in rlimits:
            resource.setrlimit(*i)

    tmpdir = context.get('csq_sandbox_dir', '/tmp/sandbox')
    this_one = hashlib.sha512('%s-%s' % (context.get('cs_username', 'None'),
                                         time.time())).hexdigest()
    tmpdir = os.path.join(tmpdir, this_one)
    os.makedirs(tmpdir, 0o777)
    for f in options['FILES']:
        typ = f[0].strip().lower()
        if typ == 'copy':
            shutil.copyfile(f[1], os.path.join(tmpdir, f[2]))
        elif typ == 'string':
            with open(os.path.join(tmpdir, f[1]), 'w') as f:
                f.write(f[2])
    fname = '%s.py' % this_one
    with open(os.path.join(tmpdir, fname), 'w') as f:
        f.write(code.replace('\r\n', '\n'))

    interp = context.get('csq_python_interpreter', sys.executable)

    p = subprocess.Popen([interp, '-E', '-B', fname],
                         cwd=tmpdir,
                         preexec_fn=limiter,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    killer = PKiller(p, options['CLOCKTIME'])
    killer.start()

    out, err = p.communicate(options['STDIN'])

    shutil.rmtree(tmpdir, True)

    return fname, out, err
