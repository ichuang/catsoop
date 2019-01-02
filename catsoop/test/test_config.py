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

cs_dummy_username = "tester"

cs_lti_config = {
    "consumers": {"__consumer_key__": {"secret": "__lti_secret__"}},
    "session_key": "12i9slfd",
    "pylti_url_fix": {
        "https://localhost": {"https://localhost": "http://192.168.33.10"}
    },
    "lti_username_prefix": "lti_",
    "force_username_from_id": False,
}

cs_data_root = os.environ["CATSOOP_DATA_DIR"]

cs_unit_test_course = "test_course"
