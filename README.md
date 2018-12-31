[![Build Status](https://travis-ci.org/ichuang/catsoop.svg?branch=master)](https://travis-ci.org/ichuang/catsoop)

```
\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_
```

#  CAT-SOOP

* Web Site:
    https://catsoop.mit.edu

* Clone Repository:
    hg clone https://catsoop.mit.edu/repo/cat-soop
    git clone https://catsoop.mit.edu/gitrepo cat-soop

* Repository Web Access:
    https://catsoop.mit.edu/repo/cat-soop

* Bug Tracker:
    https://catsoop.mit.edu/bugs

* IRC:
    #cat-soop on OFTC (irc.oftc.net)

* Mailing List:
    catsoop-users@mit.edu
    (subscribe at http://mailman.mit.edu/mailman/listinfo/catsoop-users)

* No animals were harmed in the making of this CAT-SOOP.


## WHAT IS IT?

CAT-SOOP is a tool for automatic collection and assessment of online exercises,
originally developed primarily for use in MIT's 6.01 (Introduction to
Electrical Engineering and Computer Science via Robotics).

CAT-SOOP is free/libre software, available under the terms of the GNU Affero
General Public License, version 3+.  Please note that the terms of this license
apply to the CAT-SOOP system itself and any plugins in use, but not to any
course material hosted on a CAT-SOOP instance, unless explicitly stated
otherwise.


## HOW DO I INSTALL IT?

See the "installation quick-start guide" at:
    https://catsoop.mit.edu/website/docs/installing

### Installation (via setuptools or pip)

To install, for example, run:

    python setup.py develop

or

    python setup.py install

## Running and configuring

To start catsoop, ensure you have a valid config.py in the current directory, and run:

    catsoop runserver

To generate a config.py file, run:

    catsoop configure

## Testing

To run all the unit tests:

    python setup.py test

## Usage

```
usage: catsoop [-h] [-v] [-c CONFIG_FILE] command

Example commands:

    runserver      : starts the CAT-SOOP webserver
    configure      : generate CAT-SOOP configuration file using an interactive wizard

positional arguments:
  command               A variety of commands are available, each with different arguments:

                        runserver      : starts the CAT-SOOP webserver
                        configure      : generate CAT-SOOP configuration file using an interactive wizard


optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase debug output verbosity
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        name of configuration file to use
```


## IS IT ANY GOOD?

Yes.


## INCLUDED SOFTWARE

CAT-SOOP is built with the Python programming language, version 3.5+:
    https://www.python.org/

CAT-SOOP itself incorporates pieces of third-party software.  Licensing
information for the original programs is available in the
`LICENSE.included_software` file.

The CAT-SOOP distribution also includes several pieces of third-party software.
Licensing information for these programs is included in this distribution, in
the `LICENSE.bundled_software` file.
