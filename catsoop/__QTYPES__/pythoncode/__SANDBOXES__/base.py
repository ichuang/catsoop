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
import re
import ast


def _execfile(*args):
    fn = args[0]
    with open(fn) as f:
        c = compile(f.read(), fn, "exec")
    exec(c, *args[1:])


def prep_code(code, test, **kwargs):
    # code is whatever code we need to test; test is the dictionary describing
    # what test we should be running
    code = code.strip()

    if test["variable"] is not None:
        footer = "_catsoop_answer = %s" % test["variable"]
    else:
        footer = None

    code = "\n\n".join(
        (
            "import os\nos.unlink(__file__)",
            kwargs["csq_code_pre"],
            test["code_pre"],
            code,
            "pass",
            kwargs["csq_code_post"],
            test["code"],
            footer,
        )
    )
    return code


def sandbox_run_code(context, code, options, count_opcodes=False, opcode_limit=None):
    s = context.get("csq_python_sandbox", "remote")
    sandbox_file = os.path.join(
        context["cs_fs_root"], "__QTYPES__", "pythoncode", "__SANDBOXES__", "%s.py" % s
    )

    opts = dict(DEFAULT_OPTIONS)
    opts.update(context.get("csq_sandbox_options", {}))
    opts.update(options)
    sandbox = dict(context)
    _execfile(sandbox_file, sandbox)
    return sandbox["run_code"](
        context, code, opts, count_opcodes=count_opcodes, opcode_limit=opcode_limit
    )


def fix_error_msg(fname, err, offset, sub):
    sublen = sub.count("\n")

    def subber(m):
        g = m.groups()
        out = g[0]
        lineno = int(g[1])
        if lineno > (offset + sublen + 1):
            # error in test code
            out += "File <Test Code>, line %d%s" % (lineno, g[2])
        elif lineno < offset:
            # error in test code
            out += "File <Test Code Preamble>, line %d%s" % (lineno, g[2])
        else:
            # error in user-submitted code
            out += "File <User-Submitted Code>, line %d%s" % (lineno - offset, g[2])
        return out

    error_regex = re.compile('(.*?)File "%s", line ([0-9]+)(,?[\n]*)' % fname)
    err = error_regex.sub(subber, err)

    err = err.replace(fname, "TEST FILE")

    e = err.split("\n")
    if len(e) > 15:
        err = "...ERROR OUTPUT TRUNCATED...\n\n" + "\n".join(e[-10:])

    err = err.replace("[Subprocess exit code: 1]", "")
    err = re.compile('(.*?)File "app_main.py", line ([0-9]+)(,?[^\n]*)\n').sub("", err)

    return err


DEFAULT_OPTIONS = {
    "CPUTIME": 1,
    "CLOCKTIME": 1,
    "MEMORY": 32 * 1024 ** 2,
    "FILESIZE": 0,
    "BADIMPORT": [],
    "BADVAR": [],
    "FILES": [],
    "STDIN": "",
}


def truncate(out, name="OUTPUT"):
    outlines = out.split("\n")
    if len(outlines) > 15:
        outlines = outlines[:15] + ["...%s TRUNCATED..." % name]
    out = "\n".join(outlines)
    if len(out) >= 5000:
        out = out[:5000] + "\n\n...%s TRUNCATED..." % name

    return out


def sandbox_run_test(context, code, test):
    options = dict(DEFAULT_OPTIONS)
    options.update(context.get("csq_sandbox_options", {}))
    options.update(test.get("sandbox_options", {}))
    safe = safety_check(code, options["BADIMPORT"], options["BADVAR"])
    if isinstance(safe, tuple):
        return ("", ("On line %d: " % safe[0]) + safe[1], "")
    fname, out, err = sandbox_run_code(
        context,
        prep_code(code, test, **context),
        options,
        count_opcodes=test["count_opcodes"],
        opcode_limit=test["opcode_limit"],
    )
    err = truncate(err, "ERROR OUTPUT")
    err = fix_error_msg(fname, err, context["csq_code_pre"].count("\n") + 2, code)
    n = out.rsplit("---", 1)
    if len(n) == 2:  # should be this
        out, log = n
    elif len(n) == 1:  # code didn't run to completion
        if err.strip() == "":
            err = (
                "Your code did not run to completion, "
                "but no error message was returned."
                "\nThis normally means that your code contains an "
                "infinite loop or otherwise took too long to run."
            )
        log = ""
    else:  # ???
        out = ""
        log = ""
        err = "BAD CODE - this will be logged"

    out = truncate(out, "OUTPUT")

    return out.strip(), err.strip(), log.strip()


def _ast_downward_search(node, testfunc):
    """
    recursive search through AST.  if a node causes testfunc to return true,
    then return that.  otherwise, return None
    """
    out = []
    if testfunc(node):
        out.append(node)
    for i in node._hz_children:
        out.extend(_ast_downward_search(i, testfunc))
    return out


def _prepare_ast(tree, parent=None):
    """
    stupid little piece of code to add a parent pointer to all nodes
    """
    tree._hz_parent = parent
    tree._hz_children = list(ast.iter_child_nodes(tree))
    for i in tree._hz_children:
        _prepare_ast(i, tree)


def _blacklist_variable(var, blacklist=None):
    blacklist = blacklist or []
    if var.id in blacklist:
        return "Disallowed variable name: %s" % var.id
    else:
        return None


def _blacklist_import(imp, blacklist=None):
    blacklist = blacklist or []
    if isinstance(imp, ast.ImportFrom):
        for i in blacklist:
            if re.match(i, imp.module):
                return "Disallowed import from %s" % imp.module
    else:
        # is Import instance
        for n in [i.name for i in imp.names]:
            for i in blacklist:
                if re.match(i, n):
                    return "Disallowed import: %s" % n


def safety_check(code, bad_imports=None, bad_variables=None):
    """
    Return None if the code is fine; otherise, return (lineno, errmsg)
    """
    code = code.replace("\r\n", "\n").strip()  # whitespace issues...

    # parse code down into AST.   return error message on failure
    try:
        tree = ast.parse(code)
        _prepare_ast(tree)  # recursively add parent/child pointers to each node
    except:
        return "SYNTAX ERROR"  # TODO: replace this with real error message

    # collect all instances of Name not contained in an Attribute object
    search = _ast_downward_search
    vars = search(
        tree,
        lambda n: (
            isinstance(n, ast.Name)
            and (not isinstance(n._hz_parent, ast.Attribute))
            and (
                not (isinstance(n._hz_parent, ast.Assign) and n in n._hz_parent.targets)
            )
        ),
    )

    for var in vars or []:
        res = _blacklist_variable(var, bad_variables)
        if res is not None:
            return (var.lineno, res)

    # collect all imports
    imports = _ast_downward_search(
        tree, lambda n: (isinstance(n, ast.Import) or isinstance(n, ast.ImportFrom))
    )

    for imp in imports or []:
        res = _blacklist_import(imp, bad_imports)
        if res is not None:
            return (imp.lineno, res)
