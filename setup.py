# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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
#
#
# Portions of this file were forked from the setup.py file for xonsh
# (https://xon.sh/), which is available under the MIT/Expat license.

import os
import sys
import subprocess

from setuptools import setup

from catsoop import __version__ as CS_VERSION, __codename__ as CODENAME

logo = (
    "\\            "
    "\n/    /\\__/\\  "
    "\n\\__=(  o_O )="
    "\n(__________) "
    "\n |_ |_ |_ |_ "
    "\n             "
    "\n  CAT-SOOP   "
)


VERSION_FNAME = os.path.join(os.path.dirname(__file__), "catsoop", "__init__.py")
ORIGINAL_VERSION = None


def get_version_and_distance(hash_command, current_sha, tags):
    ordered_hashes = {
        hash_: ix
        for ix, hash_ in enumerate(
            reversed(subprocess.check_output(hash_command).decode("ascii").splitlines())
        )
    }
    current_rev = ordered_hashes[current_sha]
    most_recent_version = "v0.0.0"
    N = 99999999
    for t, h in tags.items():
        if t != "tip" and h in ordered_hashes:
            distance = current_rev - ordered_hashes[h]
            if 0 <= distance < N:
                N = distance
                most_recent_version = t
        if N == 0:
            break
    return most_recent_version, N


def dev_number_git():
    try:
        branch = (
            subprocess.check_output(["git", "branch", "--show-current"])
            .decode("ascii")
            .strip()
        )
        assert branch
    except:
        print("failed to find git branch", file=sys.stderr)
        return
    try:
        raw_tags = subprocess.check_output(["git", "tag"]).decode("ascii").splitlines()
        tags = {}
    except Exception:
        print("failed to read git tags", file=sys.stderr)
        return
    for t in raw_tags:
        t = t.strip()
        tags[t] = (
            subprocess.check_output(["git", "rev-parse", t]).decode("ascii").strip()
        )
    try:
        sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip()
        )
    except:
        return None
    _cmd = ["git", "log", branch, "--format=%H"]
    most_recent_version, N = get_version_and_distance(_cmd, sha, tags)
    try:
        _cmd = ["git", "show", "-s", "--format=%cD", sha]
        _date = subprocess.check_output(_cmd)
        _date = _date.decode("ascii")
        _date = "".join(_date.split(" ", 1)[1:]).strip()
    except:
        _date = ""
        print("failed to get git commit date", file=sys.stderr)
        return
    try:
        dirty = len(
            subprocess.check_output(["git", "status", "--porcelain"])
            .decode("ascii")
            .strip()
            .splitlines()
        )
    except:
        return
    return {
        "vcs": "Git",
        "shortvcs": "git",
        "branch": None if branch == "main" else branch,
        "version": most_recent_version,
        "hash": sha,
        "distance": N,
        "date": _date,
        "changes": dirty,
    }


def dev_number_hg():
    # get the current branch
    try:
        branch = subprocess.check_output(["hg", "branch"]).decode("ascii").strip()
        print(f"hg branch: {branch!r}")
    except:
        print("failed to find hg branch", file=sys.stderr)
        return
    try:
        tags = subprocess.check_output(
            ["hg", "tags", "--template", "{tags}:{node}\n"]
        ).decode("ascii")
        tags = dict(i.strip().split(":") for i in tags.splitlines())
    except Exception:
        print("failed to find hg tags", file=sys.stderr)
        return
    try:
        sha = (
            subprocess.check_output(["hg", "--debug", "id"])
            .decode("ascii")
            .strip()
            .split()[0]
            .rstrip("+")
        )
    except:
        sha = tags["tip"][1]
    _cmd = ["hg", "log", "-b", branch, "--template", "{node}\n"]
    most_recent_version, N = get_version_and_distance(_cmd, sha, tags)
    try:
        _cmd = ["hg", "log", "-r", "tip"]
        _info = subprocess.check_output(_cmd).decode("ascii")
        _info = dict(i.strip().split(" ", 1) for i in _info.strip().splitlines())
        _date = _info["date:"].strip()
    except Exception:
        _date = ""
        print("failed to get hg commit date", file=sys.stderr)
    try:
        dirty = len(
            subprocess.check_output(["hg", "status"])
            .decode("ascii")
            .strip()
            .splitlines()
        )
    except:
        return
    return {
        "vcs": "Mercurial",
        "shortvcs": "hg",
        "branch": None if branch == "default" else branch,
        "version": most_recent_version,
        "hash": sha,
        "distance": N,
        "date": _date,
        "changes": dirty,
    }


_vcs_shortname = {
    "Mercurial": "hg",
    "Git": "git",
}


def dev_number():
    return dev_number_hg() or dev_number_git()


def dirty_version():
    """
    If install/sdist is run from a git directory, add a devN suffix to reported
    version number and write an ignored file that holds info about the current
    state of the repo.
    """
    global CS_VERSION, ORIGINAL_VERSION

    dev_num = dev_number()
    if dev_num:
        CS_VERSION = dev_num["version"]
        if dev_num["distance"] != 0:
            CS_VERSION = f"%s+%s.%s.%s%s" % (
                CS_VERSION,
                dev_num["shortvcs"],
                dev_num["distance"],
                dev_num["hash"][:8],
                (".l%s" % dev_num["changes"]) if dev_num["changes"] else "",
            )
            with open(
                os.path.join(os.path.dirname(__file__), "catsoop", "dev.hash"), "w"
            ) as f:
                f.write(
                    "{}|{}|{}|{}".format(
                        dev_num["vcs"],
                        dev_num["hash"],
                        dev_num["date"],
                        dev_num["changes"],
                    )
                )
    with open(VERSION_FNAME, "r") as f:
        ORIGINAL_VERSION = f.read()
    with open(VERSION_FNAME, "w") as f:
        f.write("__version__ = %r\n" % CS_VERSION.lstrip("v"))
        f.write("__codename__= %r\n" % CODENAME)


def main():
    if sys.version_info[:2] < (3, 8):
        sys.exit("catsoop currently requires Python 3.8+")

    if "--name" not in sys.argv:
        print(logo)

    with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), "r") as f:
        requirements = f.read().split("\n")

    with open(os.path.join(os.path.dirname(__file__), "README"), "r") as f:
        readme = f.read()

    try:
        dirty_version()
        setup(
            name="catsoop",
            version=CS_VERSION.lstrip("v"),
            author="CAT-SOOP Contributors",
            author_email="catsoop-dev@mit.edu",
            packages=[
                "catsoop",
                "catsoop.test",
                "catsoop.thirdparty",
                "catsoop.scripts",
            ],
            scripts=[],
            url="https://catsoop.org",
            license="AGPLv3+",
            description="CAT-SOOP is a tool for automatic collection and assessment of online exercises.",
            long_description=readme,
            long_description_content_type="text/plain",
            include_package_data=True,
            entry_points={
                "console_scripts": ["catsoop = catsoop.__main__:command_line_interface"]
            },
            install_requires=requirements,
            extras_require={"server": ["uwsgi"]},
            package_dir={"catsoop": "catsoop"},
            package_data={"catsoop": ["scripts/*"]},
            classifiers=[
                "Development Status :: 4 - Beta",
                "Intended Audience :: Education",
                "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
                "Topic :: Education",
                "Topic :: Internet :: WWW/HTTP :: WSGI",
            ],
        )
    finally:
        if ORIGINAL_VERSION is not None:
            with open(VERSION_FNAME, "w") as f:
                f.write(ORIGINAL_VERSION)


if __name__ == "__main__":
    main()
