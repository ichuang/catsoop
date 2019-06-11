import os
import sys
import zlib
import pickle
import shutil

from datetime import datetime

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
import catsoop.base_context as bc
import catsoop.time as cstime

results = os.path.join(bc.cs_data_root, "_logs", "_uploads")
for root, dirs, files in os.walk(results):
    dirs.sort()
    if set(files) == {"info", "content"}:
        fn = os.path.join(root, "info")
        try:
            with open(fn, "r") as f:
                x = eval(f.read().strip())
            x = {
                k: cstime.detailed_timestamp(v) if isinstance(v, datetime) else v
                for k, v in x.items()
            }
        except:
            continue
        with open(fn, "wb") as f:
            f.write(cslog.prep(x))

        if bc.cs_log_compression:
            fn2 = os.path.join(root, "content")
            with open(fn2, "rb") as f:
                t = f.read()
            with open(fn2, "wb") as f:
                o = cslog.compress_encrypt(t)
                f.write(o)
        print(root, len(t), len(o))
