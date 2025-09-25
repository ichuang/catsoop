#!/usr/bin/env python3

import os
import sys
import pickle
import hashlib
import getpass

try:
    import tqdm
except:
    tqdm = None

try:
    log_backup_loc = sys.argv[1]
    assert os.path.isdir(log_backup_loc)
except:
    sys.exit("Please specify a directory containing a catsoop logs backup")


config_loc = os.environ.get(
    "CATSOOP_CONFIG",
    os.path.join(os.path.expanduser("~"), ".config", "catsoop", "config.py"),
)
os.environ["CATSOOP_CONFIG"] = config_loc
_enc_salt_file = os.path.join(os.path.dirname(config_loc), "encryption_salt")
_enc_hash_file = os.path.join(os.path.dirname(config_loc), "encryption_passphrase_hash")
if os.path.isfile(_enc_salt_file):
    with open(_enc_salt_file, "rb") as f:
        salt = f.read()
    with open(_enc_hash_file, "rb") as f:
        phash = f.read()
    print(
        "CAT-SOOP's logs are to be encrypted.  Please enter the encryption passphrase below."
    )
    while True:
        pphrase = getpass.getpass("Encryption passphrase: ")
        h = hashlib.pbkdf2_hmac("sha512", pphrase.encode("utf8"), salt, 100000)
        if h == phash:
            os.environ["CATSOOP_PASSPHRASE"] = pphrase
            break
        else:
            sys.exit("Passphrase does not match stored hash.  Exiting.")


def _dots(x, start=""):
    l = len(x)
    for ix, i in enumerate(x):
        print(f"{start} {ix}/{l} ({ix / l * 100:.02f}%)", flush=True)
        yield i
    print()


import catsoop.cslog as cslog  # should be OK here?


# CONVERT UPLOADS

upload_id_map = {}
uploads_dir = os.path.join(log_backup_loc, "_uploads")
if os.path.isdir(uploads_dir):
    for root, dirs, files in os.walk(uploads_dir):
        if len(files) == 2:
            u = root.split(".")[-1]
            with open(os.path.join(root, "info"), "rb") as f:
                info = pickle.load(f)
            with open(os.path.join(root, "content"), "rb") as f:
                content = f.read()
            upload_id_map[u] = cslog.store_upload(
                info["username"], content, info["filename"]
            )
            print(
                "Upload:",
                f"{u[:8]}... -> {upload_id_map[u][:8]}...",
            )


def _transform_submission(sub):
    if isinstance(sub, list):
        return {
            "type": "file",
            "name": sub[0],
            "id": upload_id_map[sub[1].split(".")[-1]],
        }
    else:
        return {"type": "raw", "data": sub}


# do regular logs

dropdirs = (
    "_checker",
    "_uploads",
    "_queues",
    ".git",
    ".hg",
    "_checker_results",
    "_sessions",
)
for root, dirs, files in os.walk(log_backup_loc):
    dirs.sort()
    files.sort()
    for dname in dropdirs:
        try:
            dirs.remove(dname)
        except:
            pass

    for f in files:
        full = os.path.join(root, f)
        relative = full[len(log_backup_loc) :].split(os.sep)

        if not relative:
            continue
        if relative[0] == "":
            relative = relative[1:]
        logname = relative.pop().rsplit(".", 1)[0]
        if not relative:
            continue

        if relative[0] == "_courses":
            try:
                course = relative[1]
                uname = relative[2]
                path = [course, *relative[3:]]
            except:
                continue
        else:
            path = []
            uname = relative[0]

        # special case: handle api tokens differently for catsoop 2021.9
        if uname == "_api_users":
            continue

        if uname == "_api_tokens":
            with open(full, "rb") as f:
                _ = f.read(8)
                uinfo = pickle.load(f)
            if not uinfo:
                continue
            uname = uinfo["username"]
            cslog.overwrite_log("_api_tokens", path, logname, uinfo["username"])
            cslog.update_log("_api_users", [], uinfo["username"], logname)
            print("API Token:", uname)
        else:
            with open(full, "rb") as f:
                while True:
                    f.read(8)
                    try:
                        e = pickle.load(f)
                    except:
                        break
                    if logname == "problemactions":
                        if "submitted" in e:
                            for i in e["submitted"]:
                                e["submitted"][i] = _transform_submission(
                                    e["submitted"][i]
                                )
                    elif logname == "problemstate":
                        for i in e["last_submit"]:
                            e["last_submit"][i] = _transform_submission(
                                e["last_submit"][i]
                            )
                    cslog.update_log(uname, path, logname, e)
                    f.read(8)
            print("Log:", uname, path, logname)

# CONVERT CHECKER RESULTS

_hex = "0123456789abcdef"
checker_dir = os.path.join(log_backup_loc, "_checker", "results")
if os.path.isdir(checker_dir):
    print("Converting checker results")
    for c1 in _hex:
        for c2 in _hex:
            this_dir = os.path.join(checker_dir, c1, c2)
            results = sorted(os.listdir(this_dir))

            for ix, r in enumerate(results):
                with open(os.path.join(this_dir, r), "rb") as f:
                    result = pickle.load(f)

                magic = r

                newloc = os.path.join(
                    os.path.expanduser("~"),
                    ".local",
                    "share",
                    "catsoop",
                    "_logs",
                    "_checker",
                    "results",
                    magic[0],
                    magic[1],
                )
                os.makedirs(newloc, exist_ok=True)
                with open(os.path.join(newloc, magic), "wb") as f:
                    f.write(cslog.prep(result))
                print("Checker:", magic)
