import os
import ast
import sys

import catsoop.cslog as cslog
import catsoop.base_context as bc

logroot = os.path.join(bc.cs_data_root, "_logs")
for root, dirs, files in os.walk(logroot):
    if ".git" in dirs:
        dirs.remove(".git")
    dirs.sort()
    for fn in sorted(files):
        if not fn.endswith(".log"):
            continue
        path = root[len(logroot) + 1 :].split(os.sep)
        if path[0] in {"_checker", "_uploads"} or path[0].startswith("."):
            # uploads don't need to be converted, and we'll convert checker
            # separately
            continue
        elif path[0] == "_courses":
            logpath = [path[1]] + path[3:]
            loguser = path[2]
            logname = fn[:-4]
        else:
            logpath = []
            loguser = path[0]
            logname = fn[:-4]
        try:
            with open(os.path.join(root, fn), "r") as f:
                data = f.read().split("\n\n")
        except:
            continue
        os.unlink(os.path.join(root, fn))
        for d in data:
            if not d:
                continue
            try:
                d = eval(d)
            except:
                print("BAD?")
                continue
            cslog.update_log(loguser, logpath, logname, d)
        print(loguser, "/".join(logpath), logname)
