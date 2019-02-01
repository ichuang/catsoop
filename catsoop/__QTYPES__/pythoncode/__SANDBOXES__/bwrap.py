# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
import uuid
import fcntl
import shutil
import tempfile
import resource
import subprocess

default_ro_bind = [
    ("/usr", "/usr"),
    ("/lib", "/lib"),
    ("/lib64", "/lib64"),
    ("/bin", "/bin"),
    ("/sbin", "/sbin"),
]


def run_code(context, code, options, count_opcodes=False, opcode_limit=None):
    def limiter():
        os.setsid()
        context["csm_process"].set_pdeathsig()()

    tmpdir = context.get("csq_sandbox_dir", "/tmp/sandbox")
    this_one = "_%s" % uuid.uuid4().hex
    tmpdir = os.path.join(tmpdir, this_one)
    with open(
        os.path.join(
            context["cs_fs_root"],
            "__QTYPES__",
            "pythoncode",
            "__SANDBOXES__",
            "_template.py",
        )
    ) as f:
        template = f.read()
    template %= {
        "enable_opcode_count": count_opcodes,
        "test_module": this_one,
        "opcode_limit": opcode_limit or float("inf"),
    }
    os.makedirs(tmpdir, 0o777)
    with open(os.path.join(tmpdir, "run_catsoop_test.py"), "w") as f:
        f.write(template)
    for f in options["FILES"]:
        typ = f[0].strip().lower()
        if typ == "copy":
            shutil.copyfile(f[1], os.path.join(tmpdir, f[2]))
        elif typ == "string":
            with open(os.path.join(tmpdir, f[1]), "w") as fileobj:
                fileobj.write(f[2])
    ofname = fname = "%s.py" % this_one
    with open(os.path.join(tmpdir, fname), "w") as fileobj:
        fileobj.write(code.replace("\r\n", "\n"))

    interp = context.get(
        "csq_python_interpreter", context.get("cs_python_interpreter", "python3")
    )

    args = [
        "bwrap",
        "--bind",
        tmpdir,
        "/run",
    ]
    supplied_args = context.get("csq_bwrap_arguments", None)
    if supplied_args is None:
        args.extend(
            [
                "--unshare-all",
                "--chdir",
                "/run",
                "--hostname",
                "sandbox-runner",
                "--die-with-parent",
            ]
        )
        for i in default_ro_bind + context.get("csq_bwrap_extra_ro_binds", []):
            args.append("--ro-bind")
            args.extend(i)
        args.extend(context.get("csq_bwrap_extra_arguments", []))
    else:
        args.extend(supplied_args)

    p = subprocess.Popen(
        args + [interp, "-E", "-B", "run_catsoop_test.py"],
        preexec_fn=limiter,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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

    files = []
    for root, _, fs in os.walk(tmpdir):
        lr = len(root)
        for f in fs:
            fname = os.path.join(root, f)
            with open(fname, "rb") as f:
                files.append((fname[lr:], f.read()))

    shutil.rmtree(tmpdir, True)

    n = out.rsplit("---", 1)
    log = {}
    if len(n) == 2:  # should be this
        out, log = n
        try:
            log = context["csm_cslog"].unprep(log.strip().encode("utf8"))
        except:
            log = {}

    if log == {} or log.get("opcode_limit_reached", False):
        if err.strip() == "":
            err = (
                "Your code did not run to completion, "
                "but no error message was returned."
                "\nThis normally means that your code contains an "
                "infinite loop or otherwise took too long to run."
            )

    if len(n) > 2:  # ???
        out = ""
        log = {}
        err = "BAD CODE - this will be logged"

    return {"fname": fname, "out": out, "err": err, "info": log}
