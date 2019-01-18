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
#
#
# Portions of this file were forked from the setup.py file for xonsh
# (https://xon.sh/), which is available under the MIT/Expat license.

import os
import sys
import subprocess

from setuptools import setup

from catsoop import __version__ as CS_VERSION

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


def dirty_version():
    """
    If install/sdist is run from a git directory, add a devN suffix to reported
    version number and write a gitignored file that holds the git hash of the
    current state of the repo.
    """
    global CS_VERSION, ORIGINAL_VERSION
    try:
        last_version = subprocess.check_output(
            ["git", "describe", "--tags", "--match", "v*"]
        ).decode("ascii")
    except Exception:
        print("failed to find git tags", file=sys.stderr)
        return
    try:
        _, N, sha = last_version.strip().split("-")
        N = int(N)
    except ValueError:  # tag name may contain "-"
        print("failed to parse git version", file=sys.stderr)
        return

    # if we get to this point, we are not at a particular tag.  we'll modify
    # the __version__ from catsoop/__init__.py to include a .devN suffix.
    sha = sha.lstrip("g")
    CS_VERSION = CS_VERSION + ".dev%s" % (N,)
    _cmd = ["git", "show", "-s", "--format=%cD", sha]
    try:
        _date = subprocess.check_output(_cmd)
        _date = _date.decode("ascii")
        # remove weekday name for a shorter string
        _date = "".join(_date.split(" ", 1)[1:])
    except:
        _date = ""
        print("failed to get commit date", file=sys.stderr)
    with open(
        os.path.join(os.path.dirname(__file__), "catsoop", "dev.githash"), "w"
    ) as f:
        f.write("{}|{}".format(sha, _date))
    with open(VERSION_FNAME, "r") as f:
        ORIGINAL_VERSION = f.read()
    with open(VERSION_FNAME, "w") as f:
        f.write('__version__ = "%s"\n' % CS_VERSION)


def main():
    if sys.version_info[:2] < (3, 5):
        sys.exit("catsoop currently requires Python 3.5+")

    if "--name" not in sys.argv:
        print(logo)

    with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), "r") as f:
        requirements = f.read().split("\n")

    with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as f:
        readme = f.read()

    try:
        dirty_version()
        setup(
            name="catsoop",
            version=CS_VERSION,
            author="CAT-SOOP Contributors",
            author_email="catsoop-dev@mit.edu",
            packages=[
                "catsoop",
                "catsoop.test",
                "catsoop.thirdparty",
                "catsoop.scripts",
            ],
            scripts=[],
            url="https://catsoop.mit.edu",
            license="AGPLv3+",
            description="CAT-SOOP is a tool for automatic collection and assessment of online exercises.",
            long_description=readme,
            long_description_content_type="text/markdown",
            include_package_data=True,
            entry_points={
                "console_scripts": ["catsoop = catsoop.main:command_line_interface"]
            },
            install_requires=requirements,
            package_dir={"catsoop": "catsoop"},
            package_data={"catsoop": ["scripts/*"]},
            test_suite="catsoop.test",
            classifiers=[
                "Development Status :: 4 - Beta",
                "Intended Audience :: Education",
                "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
                "Programming Language :: Python :: 3.5",
                "Programming Language :: Python :: 3.6",
                "Programming Language :: Python :: 3.7",
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
