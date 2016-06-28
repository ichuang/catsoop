# Version 9.0.0 (current progress)

_Next planned release.  Currently under development._

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

* `.pycs` compiled CAT-SOOP source files' names now include the Python
    implementation's cache tag, so that the same course can be migrated to a
    CAT-SOOP instance running a different version of CAT-SOOP without issue.

**Security:**

# Version 8.0.0

**Added:**

* `<label>` and `<ref>` tags are now available, for easier referencing of
    sections within a CAT-SOOP page.
* Answers and explanations can now be automatically viewed in certain
    situations (running out of submissions, earning 100% score).
* Added a check for non-ASCII characters in input, and an error message to be
    displayed in this case.
* Most CAT-SOOP options related to the default handler can now be specified as
    functions that return the appropriate value, rather than the value itself,
    which allows them to be set in a way that depends on the current context.
* Added a way to compute stats about a particular page (for use in making
    gradebooks).
* Question types can now have multiple form fields by having names starting with
    `__QNAME_`, where `QNAME` is the name of the question.
* The `multiplechoice` question type has two new modes which allow for arbitrary
    formatting (including math) in the options: `checkbox`, which allows
    multiple answers to be selected; and `radio`, which allows only one answer
    to be selected.
* Added the `cs_debug` function, which can be used to log arbitrary information
    to a file during execution of a `preload` or `content` file.
* Resources can now be loaded from arbitrarily-named files
    (e.g., `<root>/path/to/foo.md` instead of `<root>/path/to/foo/content.md`)
* In the `pythoncode` question type, it is now possible to hide the code
    associated with test cases.
* Added `data_uri` module from
    [https://gist.github.com/zacharyvoase/5538178](https://gist.github.com/zacharyvoase/5538178)
    for better handling of file uploads
* Users can now log in with their e-mail addresses instead of their usernames
    when using the `login` authentication type.
* Permissions can now be specified directly via `cs_permissions`, instead of
    exclusively via roles.
* The `pythoncode` question type can now handle Python 3 code.
* Handlers and question types can now have viewable pages inside them, viewable
    at `<url_root>/__HANDLER__/default/page_name`
* Every page footer now links to both the terms of the license, and also to the
    "download source" link.
* Added a module for sending e-mails, primarily for use in the `login`
    authentication type.
* MathJax is now included directly, rather than loaded from their CDN.

**Changed:**

* Functions inside of question types no longer need to manually load default
    values; values from the `defaults` variable are automatically used when not
    specified inside the `<question>` tag.
* The `login` authentication type was much improved, including the option to
    send confirmation e-mails, change passwords, and recover lost passwords; and
    to customize the types of e-mail addresses that are accepted.
* Improved error reporting in the `login` question type.
* The `cs_post_load` hook now executes before the page's handler is invoked,
    and a new hook `cs_post_handle` was introduced, which is called after the
    handler is invoked.
* CAT-SOOP's handling of HTML tags is now case-insensitive.
* The "view as" page was updated to show more accurately what the user in
    question would see.
* Many options related to the default handler (primarily related to which
    actions should be allowed) are now specified on a per-question basis rather
    than a per-page basis.
* Locking a user out of a problem has been separated from viewing the answer to
    that question.
* Improved rendering in the `expression` question type.
* `name_map` is now stored as an ordered dictionary.
* Results from the `pythonic` question type are now evaluated in the question's
    scope, rather than in the question type's scope.
* The number of rows to be displayed in the ACE interface for coding questions
    is now customizable.
* Answers in the `smallbox` and `bigbox` question types are no longer wrapped in
    `<tt></tt>`
* Markdown and/or custom XML, depending on the source type used, is now
    interpreted inside of answers and explanations (including math rendering).
* All CAT-SOOP modules are now available inside of the source files for handlers
    and question types.
* The `cs_scripts` string is now injected into the template after jQuery, katex,
    MathJax, and cs_math have been loaded.
* Modified the generation of per-user random seeds to (eventually) allow for
    re-generating of random seeds.
* Moved much of the Javascript code from the default handler to separate files.
* Moved WSGI file and changed the way imports are handled in order to make sure
    everything can access the CAT-SOOP modules/subpackages.
* Moved handling of `csq_prompt` out of individual question types and into the
    default handler to avoid duplicating code.
* Removed logo image from main page.
* `cs_source_format` is now inferred (rather than specified explicitly).

**Fixed:**

* Fixed a bug whereby `$` characters could not be escaped with `\`.
* Fixed issues with certain tags' internals being parsed as Markdown 
    (`script`, `pre`, `question`, etc).
* Trying to access a resource that doesn't exist on disk now gives a 404 error
    instead of crashing.
* Fixed several bugs related to uploading multiple files in a single submission
* Spaces are now allowed in question names.
* CAT-SOOP no longer crashes on a malformed `<question>`, but rather displays an
    error message.
* Fixed an issue with intermittent WSGI failures by re-trying failed actions.
* Updated MathJax to version 2.6.1 to fix a rendering issue in Chrome.
* Updated the URL of the default Python sandbox to reflect changes in the
    CAT-SOOP web site.
* Improved handling of query strings and fragment identifiers when rewriting
    URLs.
* Improved handling of implicit multiplication in the `expression` question
    type.
* Added unary `+` to Python syntax in the `expression` question type.
* `cslog.most_recent` now returns the default value when the log file does not
    exist, instead of crashing.
* Fixed handling of temporary files on Windows hosts.
* Fixed validation of user information when registering under the `login`
    authenatication type.
* Fixed several bugs with manual grading, reported from 6.02.
* Log files are no longer created when trying to read from a nonexistent log.
* Mercurial temporary files (`*.orig`) are now ignored in the zip generated when
    downloading the source.
* `<pre>` tags are now used instead of `<tt>` for wrapping answers in the
    `pythoncode` question type.
* Fixed an issue in the `pythoncode` sanboxes whereby `0 MEMORY` limit actually
    allowed 0 bytes of heap storage, rather than unlimited.
* Prevent a crash if `<cs_data_root>/courses` does not exist.
* Modified to always use the local `markdown` package, even if one is installed
    globally, to make sure Markdown extensions are loaded properly.

**Security:**

* Smarter hashing (`PBKDF2`) is now used for the `login` authentication mode.
* Closed a XSS vulnerability in the `pythoncode` question type.
* Closed a security hold in session handling that allowed for arbitrary code
    execution under certain circumstances by validating session ids and
    modifying the way session data are stored.
* Logs can no longer be accessed/created outside of the appropriate `__LOGS__`
    directories.

# Version 7.1.1

**Fixed:**

* Fixed an issue that prevented the last question on each page from being
    displayed.

# Version 7.1.0

**Added:**

* Included python-markdown from
    [https://pypi.python.org/pypi/Markdown](https://pypi.python.org/pypi/Markdown)
* Added the option to grade questions manually, from 6.02 fall 2015.
* Added a `richtext` question type, which allows for formatting of text using
    CAT-SOOP-flavored Markdown.
* Added the `fileupload` question type, which allows users to upload arbitrary
    files.

**Changed:**

* Rewrote the `expression` question type to use PLY for parsing, and included
    a default syntax for expressions that is more approachable to users not
    familiar with Python.

# Version 7.0.1

**Fixed:**

* Fixed a breaking syntax error in the `expression` question type.

# Version 7.0.0

**Added:**

**Changed:**

* Complete rewrite of sandboxing for Python code.

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 6.0.0

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 5.0.0

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 4.0.0

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 3.0.1

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 3.0.0

_Complete re-write.  First version used in 6.01 (spring 2013).  First version
with any similarity to the current code._

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 2.0.0

_Lost to the ages._

# Version 1.0.0

_The original version, used in 6.003 fall 2011, and described in
[http://hdl.handle.net/1721.1/77086](http://hdl.handle.net/1721.1/770860),
which has very little relevance to later versions._
