import os
import sys
import json
import subprocess
import sqlite3
import zlib

this_dir = os.path.dirname(__file__)
catsoop_root = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
sys.path.append(catsoop_root)

import catsoop.cslog as cslog
import catsoop.base_context as bc

logroot = os.path.join(bc.cs_data_root, "__LOGS__")
for i in os.listdir(logroot):
    if i.endswith(".db") and i != "_queue.db" and i != "_checker.db":
        s = sqlite3.connect(os.path.join(logroot, i))
        c = s.cursor()
        c.execute("SELECT * FROM log ORDER BY ix ASC")
        r = c.fetchall()
        for row in r:
            cslog.update_log(
                i.rsplit(".", 1)[0], json.loads(row[1]), row[2], json.loads(row[3])
            )

courseroot = os.path.join(logroot, "_courses")
for i in os.listdir(courseroot):
    thisroot = os.path.join(courseroot, i)
    for j in os.listdir(thisroot):
        if j.endswith(".db"):
            n = j.rsplit(".", 1)[0]
            print(os.path.join(thisroot, j))
            s = sqlite3.connect(os.path.join(thisroot, j))
            c = s.cursor()
            c.execute("SELECT * FROM log ORDER BY ix ASC")
            r = c.fetchall()
            for row in r:
                if row[2] == "staticaccess":  # these were broken
                    cslog.update_log(
                        json.loads(row[1]), [n], row[2], json.loads(row[3])
                    )
                else:
                    cslog.update_log(n, json.loads(row[1]), row[2], json.loads(row[3]))


CHECKER_DB_LOC = os.path.join(bc.cs_data_root, "__LOGS__", "_checker")
RUNNING = os.path.join(CHECKER_DB_LOC, "running")
QUEUED = os.path.join(CHECKER_DB_LOC, "queued")
RESULTS = os.path.join(CHECKER_DB_LOC, "results")

for i in (RUNNING, QUEUED, RESULTS):
    os.makedirs(i, exist_ok=True)

s = sqlite3.connect(os.path.join(logroot, "_checker.db"))
c = s.cursor()
c.execute("SELECT * FROM checker")
r = c.fetchone()
while r is not None:
    magic = r[0]
    print(magic)
    entry = {
        "path": json.loads(r[1]),
        "username": r[2],
        "names": json.loads(r[3]),
        "form": json.loads(r[4]),
        "time": r[5],
        "action": r[7],
    }
    progress = r[6]
    if progress in (2, 3):  # this means finished.  need to get score, etc, as well
        entry["response"] = zlib.decompress(r[10])
        entry["score"] = r[8]
        entry["score_box"] = r[9]

        with open(os.path.join(RESULTS, magic), "wb") as f:
            f.write(cslog.prep(entry))
    elif progress == 1:
        with open(os.path.join(RUNNING, magic), "wb") as f:
            f.write(cslog.prep(entry))
    elif progress == 2:
        with open(os.path.join(QUEUED, "0_%s" % magic), "wb") as f:
            f.write(cslog.prep(entry))
    r = c.fetchone()
