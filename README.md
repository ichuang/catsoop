```nohighlight
\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_
```

[![Build Status](https://ci.smatz.net/api/badges/catsoop/catsoop/status.svg)](https://ci.smatz.net/catsoop/catsoop)
[![PyPI: Latest Version](https://img.shields.io/pypi/v/catsoop.svg)](https://pypi.org/project/catsoop/)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/catsoop.svg)
[![License: AGPLv3+](https://img.shields.io/pypi/l/catsoop.svg)](https://hz.mit.edu/git/catsoop/catsoop/raw/branch/master/LICENSE)
# CAT-SOOP

* Web Site: https://catsoop.mit.edu

* Clone Repository: `git clone https://hz.mit.edu/git/catsoop/catsoop.git`

* Repository Web Access: https://hz.mit.edu/git/catsoop/catsoop

* Bug Tracker: https://hz.mit.edu/git/catsoop/catsoop/issues

* IRC: `#catsoop` on OFTC (`irc.oftc.net`)

* Mailing List: `catsoop-users@mit.edu` (subscribe at http://mailman.mit.edu/mailman/listinfo/catsoop-users)


## WHAT IS IT?

CAT-SOOP is a tool for automatic collection and assessment of online exercises, originally developed primarily for use in MIT's 6.01 (Introduction to Electrical Engineering and Computer Science via Robotics).

CAT-SOOP is free/libre software, available under the terms of the GNU Affero General Public License, version 3+.  Please note that the terms of this license apply to the CAT-SOOP system itself and any plugins in use, but not to any course material hosted on a CAT-SOOP instance, unless explicitly stated otherwise.


## HOW DO I INSTALL IT?

To install, run:

```nohighlight
pip3 setup.py install
```

Or, from a clone of the repository, run:

```nohighlight
python setup.py install
```

#### Configuring

To generate a config.py file, run:

```nohighlight
catsoop configure
```

If you are setting up a public-facing copy of CAT-SOOP (as opposed to a local copy for debugging purposes), see the instructions at https://catsoop.mit.edu/website/docs/installing/server_configuration

#### Running

To start the server, run:

```nohighlight
catsoop runserver
```

#### Testing

To run all the unit tests:

```nohighlight
python setup.py test
```


## IS IT ANY GOOD?

Yes.


## INCLUDED SOFTWARE

CAT-SOOP incorporates pieces of third-party software.  Licensing information for the original programs is available in the `LICENSE.included_software` file.  The CAT-SOOP distribution also includes several pieces of third-party software.  Licensing information for these programs is included in this distribution, in the `LICENSE.bundled_software` file.
