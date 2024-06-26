#!/usr/bin/env python3

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

import catsoop.base_context

import sys


TEMPLATE = """
        location ~ ^%(url_endpoint)s/_base/(?<path>.*)/(?<filename>[^\/]*) {
           root %(cs_fs_root)s/__STATIC__;
           try_files /$path/$filename =404;
        }

        location ~ ^%(url_endpoint)s/_handler/(?<handler>[^\/]*)/(?<path>.*) {
           root %(cs_fs_root)s/__HANDLERS__;
           try_files /$handler/__STATIC__/$path =404;
        }
        location ~ ^%(url_endpoint)s/_auth/(?<auth>[^\/]*)/(?<path>.*) {
           root %(cs_fs_root)s/__AUTH__;
           try_files /$auth/__STATIC__/$path =404;
        }
        location ~ ^%(url_endpoint)s/_qtype/(?<qtype>[^\/]*)/(?<path>.*) {
           root %(cs_fs_root)s/__QTYPES__;
           try_files /$qtype/__STATIC__/$path =404;
        }

        location ~ ^%(url_endpoint)s/_plugin/(?<plugin>[^\/]*)/(?<path>.*) {
           root %(cs_data_root)s/plugins;
           try_files /$plugin/__STATIC__/$path =404;
        }

        location ~ ^%(url_endpoint)s/(?<course>[^\/]*)(?<path>.*)/(?<filename>[^\/]*) {
           root %(cs_data_root)s/courses;
           try_files /$course$path/__STATIC__/$filename /$course/__STATIC__$path/$filename =404;
        }
"""


def main(argv):
    try:
        URL_ROOT = argv[1]
    except:
        sys.exit(
            """Please specify the relative URL endpoint of your catsoop install, e.g. / or /catsoop"""
        )

    print(
        TEMPLATE
        % {
            "cs_fs_root": catsoop.base_context.cs_fs_root,
            "cs_data_root": catsoop.base_context.cs_data_root,
            "url_endpoint": URL_ROOT.strip().rstrip("/"),
        }
    )


if __name__ == "__main__":
    main(sys.argv)
