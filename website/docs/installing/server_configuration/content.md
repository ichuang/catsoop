<python>
cs_content_header = cs_long_name
</python>

This page describes a fairly typical CAT-SOOP setup, and assumes that you have
already installed and configured CAT-SOOP as described on [this
page](CURRENT/..).

<tableofcontents/>

<section>Check Web Settings</section>

To start, double-check the following values in `config.py`:

* `cs_url_root`, which is the URL of the root of the CAT-SOOP installation.
* `cs_checker_websocket`, which tells CAT-SOOP where clients can make websocket connections to the checker.

For example:

```
cs_url_root = 'http://localhost:6010'
cs_checker_websocket = 'ws://localhost:6011'
```

Typically, on a public-facing server, `cs_url_root` will start with `https`,
and `cs_checker_websocket` will start with `wss`.

<div class="callout callout-warning">
<h4>Double Check</h4>
<p>Make sure that the <code>cs_fs_root</code> directory can be read from and written to by
the web server's user.</p>
<p>Make sure that the <code>cs_data_root</code> directory is <b>not</b> web-accessible, and that
the web server's user has read/write access.</p>
</div>

By default, running `catsoop start` will start several processes.  The most
important are the UWSGI server (default port `6010`) and the websocket server
(default port `6011`).  You can change these ports by setting additional
variables `cs_wsgi_server_port` and `cs_checker_server_port`, respectively, in
your `config.py`.

<section>Configure nginx</section>

Next, we will configure nginx to redirect relevant traffic to the web server
and the websocket server.

Start by creating a new file in `/etc/nginx/sites-available` with the following
content, which will configure nginx to route certain requests to CAT-SOOP, and
to redirect all traffic to HTTPS.

You can, of course, customize the endpoints (`/cat-soop` and `/reporter` in the
example below) to change the base URL for both the WSGI server and the
websocket server.

<div class="callout callout-info">
<h4>Note</h4>
If you do not already have one and you are planning to make a public-facing
server, you should acquire an SSL certificate.  If your server is running at
MIT, you can follow the instructions <a
href="http://kb.mit.edu/confluence/display/istcontrib/Obtaining+an+SSL+certificate+for+a+web+server"
target="_blank">on this page</a>.  Otherwise, SSL/TLS Certificates are
available gratis from <a href="https://letsencrypt.org/" target="_blank">Let's
Encrypt</a>.
</div>


```
# redirect all HTTP traffic to HTTPS
server {
	listen 80;
	listen [::]:80;
	return 301 https://$host$request_uri;
}

server {
    # listen on port 443 (standard port for HTTPS traffic) and enable SSL
	listen 443 ssl;
	listen [::]:443 ssl;

    # the following should reference your SSL cert and key file
	ssl_certificate	    /path/to/certificate-chain.crt;
	ssl_certificate_key /path/to/keyfile.key;

    # by default, serve files from /var/www/html
	root /var/www/html;

    # set the server's name (change this to reflect your server's FQDN)
	server_name your.server.com;

    # try adding trailing slashes before 404'ing
	location / {
		try_files $uri $uri/ =404;
	}

    # ignore .ht* files
	location ~ /\.ht {
		deny all;
	}

    # the following will route requests to https://your.server.com/cat-soop
    # to the uWSGI server.  change "cat-soop" in the following lines if you
    # want to use a different URL.
    location /cat-soop {
            rewrite /cat-soop/?(.*) /$1 break;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_cache_bypass $http_upgrade;
            proxy_pass http://localhost:6010/;
    }

    # the following will route websocket requests to
    # wss://your.server.com/reporter to CAT-SOOP's websocket server.
    location /reporter {
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_cache_bypass $http_upgrade;
            proxy_pass http://localhost:6011/;
    }
}
```

<div class="callout callout-warning">
<h4>Double Check</h4>
<p>Note that your <code>cs_url_root</code> and <code>cs_checker_websocket</code> should match the nginx configuration.  In the example above, we should have <code>cs_url_root = 'https://your.server.com/cat-soop'</code> and <code>cs_checker_websocket = wss://your.server.com/reporter</code> in the <code>config.py</code> file.</p> <p>
Also, make sure the ports (<code>6010</code> and <code>6011</code> in the example above) match the port numbers you set in <code>config.py</code>, if any.
</p>
</div>


<div class="callout callout-info">
<h4>Note</h4>
If you want the root of the webserver to point to the CAT-SOOP instance, you
can remove the block labeled <code>location /</code> from the example above,
change <code>location /cat-soop</code> to be <code>location /</code>, and
comment out the <code>rewrite</code> line within that block.
</div>

<subsection>(Optional) Client Certificate Authentication</subsection>

If you would like to enable authentication based on client certificates (instead of username/password), add the following line beneath the other `ssl_` configuration variables in the NGINX configuration file:

```
	ssl_client_certificate /path/to/client_ca.pem;
	ssl_verify_client on;
```

where `/path/to/client_ca.pem` is the location on fisk of the CA with which client certificates are signed.

<section>(Optional) Configure Workers</section>

<subsection>Web Server</subsection>

By default, CAT-SOOP uses [cheroot](https://github.com/cherrypy/cheroot) as its
WSGI server.  However, for public-facing instances, we recommend using [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) instead of cheroot.  To
do so, set `cs_wsgi_server = 'uwsgi'` in your `config.py` file.  To make uWSGI
spawn multiple worker processes, set the `cs_wsgi_server_min_processes` and
`cs_wsgi_server_max_processes` variables.  When using uWSGI, you do not need to
do any special NGINX configuration for load balancing.

Alternatively, if you prefer to use `cheroot`, you can cause CAT-SOOP to launch
more than one worker by setting `cs_wsgi_server_port` to a _list_ of integers
instead of a single integer.  In this case, you will also likely want to
configure NGINX to balance the load between the different processes by
following the instructions [on this
page](http://nginx.org/en/docs/http/load_balancing.html) (and, importantly,
including the `ip_hash;` directive so users' sessions are not lost).

<subsection>Checker</subsection>

By default, CAT-SOOP's checker will run at most 1 check at a time.  If you have
the resources available, you can configure the checker to run multiple checks
in parallel by setting `cs_checker_parallel_checks` to a larger (integer)
number in your `config.py`.


<section>Start CAT-SOOP</section>

From within the `scripts` directory of the CAT-SOOP source, run the following
command to start CAT-SOOP:

```
$ catsoop start
```

On a typical webserver, it is a good idea to run the command in a screen so
that the process does not die when you hang up.  Alternatively, you can use
`nohup`.  For example,

```
$ nohup catsoop start > /dev/null &
```

<section>Test Configuration</section>

Direct your web browser to your `cs_url_root` and you should now see the
CAT-SOOP default page!

<section>(Optional) Configure Backups</section>

All of CAT-SOOP's data are stored in files on disk in a directory called
`__LOGS__` in the `cs_data_root` location specified above (by default,
`~/.local/share/cat-soop`).  CAT-SOOP itself will not back these files up, but
there are many strategies for backups using common utilities.

I have used many approaches in the past, but my usual approach involves setting
the `__LOGS__` directory up as a Mercurial or Git repository, and then setting
up a cron job to commit all files in that repository and push to several
locations.  This approach has several advantages over simply using `rsync` or
`scp` to copy the folder to a remote machine.  In particular, it allows you to
roll back to any past backup while keeping size down by only storing diffs
(instead of storing a complete copy of each file for each backup).

Here, we'll set up a backup using Git (which tends to be more efficient for
this purpose, both in time and in memory, than Mercurial).  To set this up,
first move yourself to the `__LOGS__` directory and run `git init`, followed by
`git add -A .` and `git gc --aggressive`.  This will set your `__LOGS__`
directory up as a Git repository.  You can then set up a cron job to commit all
changes and push these changes to an arbitrary number of backup locations
(local or remote).

The following example script (`/home/catsoop/do_backup.sh`) was used by several
classes in fall 2018.  It commits local changes to a Git repository, and it
then pushes those changes to one local location (on a separate disk) and to one
remote location.

```bash
#!/bin/bash
cd /home/catsoop/cat-soop-data/__LOGS__;
git add -A;
git commit -m "$(date +'%Y-%m-%d:%H:%M')";
git push /storage2/backup master;
git push catsoop@cat-soop.org:backups/py master;
```

It can then be configured to run, for example, every hour at xx:05 and xx:35
with the following crontab entry:

```nohighlight
5,35 * * * * /usr/bin/flock -n /tmp/backup.lockfile /home/catsoop/do_backup.sh 2>&1 >/dev/null
```

<section>(Optional) Set Up Local Python Sandbox</section>

By default, Python code that needs to be sandboxed (for example, student code
from the `pythonic` or `pythoncode` question types) will be sent to
`cat-soop.org` to be run.

It is fine to leave things this way if you'd like.  I will keep that service up
as long as is feasible, and the sandbox doesn't log anything about the code it
runs.  That said, you may also wish to set things up so that the code runs on
your machine.  The main benefit of this approach is that you don't have to rely
on an external service (network issues or our server's downtime won't affect
you, and you have a sandbox to yourself instead of having to share with
others).

Our recommended sandboxing approach involves creating a Python virtual
environment to run student code, and limiting that interpreter's permissions
using [AppArmor](http://wiki.apparmor.net/index.php/Main_Page) and
[bubblewrap](https://github.com/projectatomic/bubblewrap).  This approach will
largely isolate the student code from the system on which it is running, and it
will also limit other resources (memory usage, etc).

<subsection>Installing Necessary Software</subsection>

In order to set things up, you'll need to install both `virtualenv` and
`AppArmor`.  On Debian Stretch, this can be done with the following commands:

```
$ sudo pip3 install virtualenv
$ sudo apt install apparmor apparmor-utils apparmor-profiles
```

You'll also need to install `bubblewrap`.  The version of `bubblewrap` that is
available in the Debian Stretch repositories does not support some of the
features we want to use, so you should compile from source.  You can do so with
the following sequence of commands (on Debian Stretch):

```
$ sudo apt build-dep bubblewrap
$ git clone https://github.com/projectatomic/bubblewrap
$ cd bubblewrap
$ ./autogen.sh
$ make
$ sudo make install
```

This will make an executable called `bwrap`, which our sandbox will use.

On Debian, you will also need to set a kernel parameter to allow unprivileged
users to create new user namespaces:

```
$ sudo sysctl kernel.unprivileged_userns_clone=1
```

You should also set this parameter in `/etc/sysctl.conf` so it persists across
reboots.

<subsection>Virtual Environment</subsection>

Now that we have all of the necessary software, we'll set up a virtual
environment.  The sandboxed code will be run in this environment.  Pick a
location (one that is readable by the user running the web server) and create a
new virtual environment there with the Python interpreter you want the checkers
to use.  In example below, we'll use the `/usr/bin/python3` interpreter, and
we'll set up the virtual environment in `/home/catsoop/python3_sandbox`.

```
$ virtualenv --always-copy -p /usr/bin/python3 /home/catsoop/python3_sandbox
```

If you want to use a different Python version as the basis for the virtual
environment, you can change the `-p` option.

<subsubsection>Installing Packages to the Sandbox</subsubsection>

If you would like your checkers to be able to use any packages outside the
standard library, you can install them in the virtual environment using the
`pip` executable within the virtual environment.  For most packages, you can
simply use the `pip` executable from this new virtual environment to install
them.  For example, to make `pillow` available within the sandbox, we could
use:

```
$ /home/catsoop/python3_sandbox/bin/pip install pillow
```

However, some packages require special care when installing.  For example,
`numpy` normally uses multiple processes when computing its results.  However,
a desirable feature of the sandbox is that it prevents student code from
launching new processes of any kind.  To get around this, it is possible to
compile `numpy` for the sandbox with all optimizations disabled, for example:

```
$ sudo apt build-dep python3-numpy
$ wget https://files.pythonhosted.org/packages/94/b8/09db804ddf3bb7b50767544ec8e559695b152cedd64830040a0f31d6aeda/numpy-1.14.4.zip
$ unzip numpy-1.14.4.zip
$ cd numpy-1.14.4
$ BLAS=None LAPACK=None ATLAS=None /home/catsoop/python3_sandbox/bin/python3 setup.py install
```

<subsection>AppArmor</subsection>

We'll use AppArmor to place some limits on our sandboxed Python interpreter.
Before we can do so, we'll have to configure the Linux kernel to use AppArmor
for security.  You can do this my modifying `/etc/default/grub`.  Within that
file, you'll need to modify a line starting with `GRUB_CMDLINE_LINUX_DEFAULT`
by adding `apparmor=1 security=apparmor` to the end of the arguments in quotes.
For example, after making this modification, this line appears on my machine
as:

```
GRUB_CMDLINE_LINUX_DEFAULT="quiet apparmor=1 security=apparmor"
```

After making this modification, you'll need to update GRUB and reboot for the
changes to take effect:

```
$ sudo update-grub
$ sudo reboot
```

After the reboot, you'll need to set up an AppArmor profile to limit your
virtual environment's Python interpreter.  Create a file
`/etc/apparmor.d/py3sandbox` containing the following, but replacing
`/home/catsoop/python3_sandbox` with your sandbox location (if it is
different), and tuning some of the other parameters if necessary:

```
#include <tunables/global>

/home/catsoop/python3_sandbox/bin/python3.6 {
    /** wrix,

    set rlimit nproc <= 0,
    set rlimit fsize <= 1M,
    set rlimit as <= 500M,
}
```

This file does a couple of things:

* It allows access to the entire filesystem.  This might seem dangerous, but we'll use `bwrap` to handle the filesystem sandboxing (though you can modify the entries above to further restrict things).
* It also introduces two resource limits:
    * student code will not be allowed to spawn any new processes
    * student code cannot write more than 1MB of data to files
    * student code will not be allowed to use more than 500MB of memory

All of these parameters are tunable, and other resources can also be limited,
as documented [here](https://linux.die.net/man/2/setrlimit).

Finally, enable the profile with the following command:

```
$ sudo aa-enforce /etc/apparmor.d/py3sandbox
```

You can then test your setup by running the Python interpreter (in our example,
`/home/catsoop/python3_sandbox/bin/python3`) and trying to write more than 1M
of data to a file:

```py
with open('/tmp/test', 'w') as f:
    f.write('a'*(1204**2+1))
```

This should produce an error, since this interpreter is not allowed to write
that much data to disk.

<div class="callout callout-info">
<h4>Note</h4>
If you did use AppArmor to place additional restrictions on filesystem access,
and if you later wish to install other Python packages for the sandboxed
interpreter, you will first need to disable the AppArmor protections by
running:
<pre>
$ sudo aa-disable /etc/apparmor.d/py3sandbox
</pre>
Then you can install the packages using the `pip` executable within the virtual
environment, and re-enable the AppArmor protections afterwards by running:
<pre>
$ sudo aa-enforce /etc/apparmor.d/py3sandbox
</pre>
</div>
</abstractions></abstractions></tunables>

<subsection>CAT-SOOP Configuration</subsection>

Now that we have those pieces set up, we'll need to configure CAT-SOOP to use
this new sandbox.

Add the following to your `preload.py` (so that all pages in the course inherit
it), substituting your own values where appropriate:

```python
csq_python_sandbox = 'bwrap'

# the following should match the line in /etc/apparmor.d/py3sandbox exactly
csq_python_interpreter = '/home/catsoop/python3_sandbox/bin/python3.6'

csq_bwrap_extra_ro_binds = [('/home/catsoop/python3_sandbox', '/home/catsoop/python3_sandbox')]
```

The `csq_bwrap_extra_ro_binds` variable tells bubblewrap to mount certain
directories from the base system on the virtual filesystem available to the
student's code in rea-only mode.  In our case, it is necessary to include the
directory from which our Python executable is available.

And that's it!  It is worth runing a few tests after implementing this, to make
sure things are working properly.  For example, I would usually try to:

* call `os.fork()` and/or use the `subprocess` module to start a child process
* write too much data to a file
* list the files in a directory not included in the sandbox (e.g., someone's home directory)
* use too much memory
* cause an infinite loop

If the system properly stops the code from running in all of the examples above
but works for a correct solution, then you're probably in good shape!
