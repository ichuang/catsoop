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
import logging


def setup_logging(context):
    logging.getLogger("pylti.common").setLevel(
        context.get("cs_lti_debug_level", "WARNING")
    )
    logging.getLogger("cs").setLevel(context.get("cs_debug_level", "WARNING"))
    logging.basicConfig(format="%(asctime)s - %(message)s")


LOGGER = logging.getLogger("cs")
