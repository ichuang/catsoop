<python>
cs_content_header = cs_long_name
</python>

This page is designed to help you get an instance of CAT-SOOP up and running.
If you are setting things up on a local copy, following the instructions on
this page should be enough.  If you are setting up a public-facing instance on
a server you control, you should follow these instructions, and then continue
by following the link at the bottom of this page for more information about
server configuration.

As a general rule, I only test using Debian GNU/Linux, but others have tested
these instructions on Mac OSX and on Windows (Cygwin or LSW).

<tableofcontents/>

<section>Install Necessary Software</section>

CAT-SOOP depends on Python (version 3.5+, with pip).

You will need Python version 3.5+ on your system to run CAT-SOOP.  Many
distributions have Python 3.5+ in their package managers, though it may be
necessary to download the source from [the official Python
site](https://www.python.org/).

On Debian Stretch, you will need the `python3` and `python3-pip` packages (or a
version of Python 3.5+ installed in some other way).

<subsection>(Cygwin Only) Patch _pyio</subsection>

As of the time of this writing (December 2017), the Python version available
through Cygwin ships with a broken version of `_pyio`, which `cheroot` uses.
In order to run CAT-SOOP on a Cygwin host, edit the file
`/usr/lib/python3.6/_pyio.py` so that the first conditional (about
`sys.platform`) reads as follows:

```py
if sys.platform == 'win32':
    from msvcrt import setmode as _setmode
elif sys.platform == 'cygwin':
    import ctypes
    _cygwin1 = ctypes.PyDLL('cygwin1.dll')
    def _setmode(fd, mode):
        return _cygwin1._setmode(ctypes.c_int(fd), ctypes.c_int(mode))
else:
    _setmode = None
```

<section>Download CAT-SOOP</section>

There are several ways you can install CAT-SOOP (as of version 14.0).

<subsection>Installation via pip</subsection>

The easiest is pip, with a command like the following:

```
$ sudo pip3 install catsoop
```

<subsection>Manual Installation</subsection>

Alternatively, you can clone the Mercurial repository (or the Git mirror):

* Mercurial: `@{TOR_STRING('hg')} clone @{cs_url_root}/repo/catsoop`
* Git: `@{TOR_STRING('git')} clone git://@{cs_url_root.split('/',2)[-1]}/catsoop.git`

After you have a local copy, you can then run:

```
$ sudo python3 setup.py install
```

from the source directory.  You can also run the unit tests by running:

```
$ sudo python3 setup.py test
```


<section>Configure CAT-SOOP</section>

To configure CAT-SOOP, run the following command:

```
catsoop configure
```

and answer the questions it poses.


<div class="callout callout-danger">
<h4>Note</h4>
If you are running a public-facing CAT-SOOP instance, you are <b>strongly
encouraged</b> to enable encryption if the directory in which you are storing
the logs is not already encrypted in some way (e.g., via <code>luks</code> or
<code>gocryptfs</code> or <code>cryfs</code>, etc).
</div>

<section>Add Courses</section>

The default location for CAT-SOOP courses is in
`~/.local/share/catsoop/courses/`.  You should move (or symlink) your courses
to that location.

<section>Start CAT-SOOP</section>

To start the server, you should run:

```
$ catsoop start
```

This will start the server listening on port 6010.  You should then be able to
directy your browser to `http://localhost:6010` to see the CAT-SOOP instance.


<section>(Optional) Sign Up for Mailing List(s)</section>

`catsoop-users@mit.edu` is a place to ask questions about CAT-SOOP usage.
You can view the archives or subscribe
[here](http://mailman.mit.edu/mailman/listinfo/catsoop-users).

`catsoop-dev@mit.edu` is the place to ask questions about CAT-SOOP development.
You can view the archives or subscribe
[here](http://mailman.mit.edu/mailman/listinfo/catsoop-dev).

<section>Additional Configuration for Public-Facing Servers</section>

If you are setting up a public-facing CAT-SOOP instance, see also [this page
about additional server configuration](CURRENT/server_configuration).
