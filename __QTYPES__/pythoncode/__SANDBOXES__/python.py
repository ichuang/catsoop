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

import os
import sys
import time
import fcntl
import shutil
import hashlib
import tempfile
import resource
import subprocess

_resource_mapper = {
    "CPUTIME": (resource.RLIMIT_CPU, lambda x: (x, x + 1)),
    "MEMORY": (resource.RLIMIT_AS, lambda x: (x, x)),
    "FILESIZE": (resource.RLIMIT_FSIZE, lambda x: (x, x)),
}


def safe_close(fd):
    try:
        os.close(fd)
    except:
        pass


def run_code(context, code, options):
    rlimits = [(resource.RLIMIT_NPROC, (0, 0))]
    for key, val in _resource_mapper.items():
        if key == "MEMORY" and options[key] <= 0:
            continue
        rlimits.append((val[0], val[1](options[key])))

    def limiter():
        os.setsid()
        for i in rlimits:
            resource.setrlimit(*i)
        context["csm_process"].set_pdeathsig()()

    tmpdir = context.get("csq_sandbox_dir", "/tmp/sandbox")
    this_one = hashlib.sha512(
        ("%s-%s" % (context.get("cs_username", "None"), time.time())).encode()
    ).hexdigest()
    tmpdir = os.path.join(tmpdir, this_one)
    os.makedirs(tmpdir, 0o777)
    for f in options["FILES"]:
        typ = f[0].strip().lower()
        if typ == "copy":
            shutil.copyfile(f[1], os.path.join(tmpdir, f[2]))
        elif typ == "string":
            with open(os.path.join(tmpdir, f[1]), "w") as fileobj:
                fileobj.write(f[2])
    fname = "%s.py" % this_one
    with open(os.path.join(tmpdir, fname), "w") as fileobj:
        fileobj.write(code.replace("\r\n", "\n"))

    interp = context.get("csq_python_interpreter", sys.executable)

    p = subprocess.Popen(
        [interp, "-E", "-B", fname],
        cwd=tmpdir,
        preexec_fn=limiter,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
    )

    out = ""
    err = ""
    try:
        out, err = p.communicate(options["STDIN"] or "", timeout=options["CLOCKTIME"])
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        out, err = p.communicate()
    out = out.decode()
    err = err.decode()

    shutil.rmtree(tmpdir, True)

    return fname, out, err
