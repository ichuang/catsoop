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
import sys
import argparse
import pkg_resources

#-----------------------------------------------------------------------------

def command_line_interface(args=None, arglist=None):
    '''
    Main catsoop command line entry point
    args, arglist are used for unit testing
    '''

    version = pkg_resources.require("catsoop")[0].version

    help_text = """
Example commands:

    runserver      : starts the CAT-SOOP webserver
    configure      : generate CAT-SOOP configuration file using an interactive wizard

"""
    cmd_help = """A variety of commands are available, each with different arguments:

runserver      : starts the CAT-SOOP webserver
configure      : generate CAT-SOOP configuration file using an interactive wizard

"""

    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", help=cmd_help)
    parser.add_argument("-v", "--verbose", help="increase debug output verbosity", action="store_true")
    default_config_location = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser(os.path.join('~', '.config')))
    default_config_location = os.path.abspath(os.path.join(default_config_location, 'cat-soop', 'config.py'))
    parser.add_argument("-c", "--config-file", help="name of configuration file to use", default=default_config_location)

    if not args:
        args = parser.parse_args(arglist)

    cfn = os.path.abspath(args.config_file)

    if args.verbose:
        os.environ['CATSOOP_DEBUG_LEVEL'] = "1"

    if args.command=="configure":
        from .scripts import configure
        configure.main()

    elif args.command=="runserver":
        from .scripts import start_catsoop
        print("cfn=%s" % cfn)
        start_catsoop.startup_catsoop(cfn)

    else:
        print("Unknown command %s" % args.command)
        sys.exit(-1)

