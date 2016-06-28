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
* Added the option to grade questions manually, from 6.02 fall 2015.
* Added a `richtext` question type, which allows for formatting of text using
    CAT-SOOP-flavored Markdown.
* Answers and explanations can now be automatically viewed in certain
    situations (running out of submissions, earning 100% score).
* Added a check for non-ASCII characters in input, and an error message to be
    displayed in this case.
* Most CAT-SOOP options related to the default handler can now be specified as
    functions that return the appropriate value, rather than the value itself,
    which allows them to be set in a way that depends on the current context.
* Added a way to compute stats about a particular page (for use in making
    gradebooks).

**Changed:**

* The `login` authentication type was much improved, including the option to
    send confirmation e-mails and recover lost passwords.
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

**Fixed:**

* Fixed a bug with escaping of `$` characters.
* Fixed issues with certain tags' internals being parsed as Markdown rather
    than "passed through."
* Trying to access a resource that doesn't exist on disk now gives a 404 error
    instead of a 500 Internal Server Error.

**Security:**

* Smarter hashing (`PBKDF2`) is now used for the `login` authentication mode.
* Closed a XSS vulnerability in the `pythoncode` question type.
* Closed a security hold in session handling that allowed for arbitrary code
    execution under certain circumstances.

# Version 7.0.1

**Added:**

**Changed:**

**Deprecated:**

**Removed:**

**Fixed:**

**Security:**

# Version 7.0.0

**Added:**

**Changed:**

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
