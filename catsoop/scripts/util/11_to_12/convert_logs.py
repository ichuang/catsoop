import os
import sys
import zlib
import pickle

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
import catsoop.base_context as bc

special_spots = {
    "_message": "cached_responses",
    "_magic": "checker_ids",
    "_score_display": "score_displays",
}

logroot = os.path.join(bc.cs_data_root, "_logs")
for root, dirs, files in os.walk(logroot):
    dirs.sort()
    for fn in sorted(files):
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
        print(loguser, logpath, logname)
        with open(os.path.join(root, fn), "rb") as f:
            sep = f.readline().strip()
            data = f.read().split(sep)
        os.unlink(os.path.join(root, fn))
        for d in data:
            try:
                d = pickle.loads(zlib.decompress(d))
            except:
                continue
            if logname == "problemstate":
                # we want to do some transformation here
                new = {"cached_responses": {}, "checker_ids": {}}
                for k, v in d.items():
                    broken = False
                    for end, newkey in special_spots.items():
                        if k.endswith(end):
                            if newkey not in new:
                                new[newkey] = {}
                            new[newkey][k[: -len(end)]] = v
                            broken = True
                            break
                    if not broken:
                        # regular key
                        new[k] = v
                d = new
            cslog.update_log(loguser, logpath, logname, d)
