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
import io

from zipfile import ZipFile, ZIP_DEFLATED

course = cs_form.get("course", None)


def keep_file(full, base):
    # ignore nohup output from scripts
    if base == "nohup.out":
        return False
    # ignore compiled python files
    if base.endswith(".pyc") or ".pycs" in base:
        return False
    # ignore vim temporary files and swap files
    if base.endswith("~") or base.endswith(".swp"):
        return False
    # ignore emacs temporary files
    if base.startswith("#") and base.endswith("#"):
        return False
    # ignore Mercurial backup files
    if base.endswith(".orig"):
        return False
    # ignore dotfiles
    if base.startswith("."):
        return False
    # ignore plugins
    if "__PLUGINS__" in full:
        return False
    # ignore config.py in catsoop root
    if full == os.path.join(cs_fs_root, "catsoop", "config.py"):
        return False
    return True


def add_files_to_zip(zipfile, base_dir, zip_base):
    for root, dirs, files in os.walk(base_dir):
        to_remove = set()
        for d in dirs:
            if d.startswith(".") or d == "node_modules":
                to_remove.add(d)
        for d in to_remove:
            dirs.remove(d)
        for f in files:
            fullname = os.path.join(root, f)
            if keep_file(fullname, f):
                name = fullname.replace(base_dir, zip_base)
                zipfile.write(fullname, name)


out_bytes = io.BytesIO()

outfile = ZipFile(out_bytes, "w", ZIP_DEFLATED)
add_files_to_zip(outfile, cs_fs_root, "catsoop-src/catsoop")
now = csm_time.from_detailed_timestamp(cs_timestamp)
now = csm_time.long_timestamp(now).replace("; ", " at ")
outfile.writestr("catsoop-src/README.txt", SOURCE_README % (cs_url_root, now))
outfile.close()

cs_handler = "raw_response"
content_type = "application/zip"
response = out_bytes.getvalue()
