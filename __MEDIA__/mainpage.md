<python>
def link(url, text=None):
    text = text or url
    return '<a href="%s" target="_blank">%s</a>' % (url, text)
</python>

<pre style="border-color:transparent; font-weight:bold; background-color:transparent;font-size:110%; color:inherit;line-height:1.1; text-align:center;">
\            
/    /\__/\  
\__=(  o_O )=
(__________) 
 |_ |_ |_ |_ 
</pre>

<center>
@{link("https://cat-soop.org")}
</center>

## About

CAT-SOOP is a tool for automatic collection and assessment of online exercises.
CAT-SOOP is @{link("https://www.fsf.org/about/what-is-free-software", "free software")},
available under the terms of the
@{link("BASE/cs_util/license", "GNU Affero General Public License, version 3")}.
In accordance with the terms of this license, the source code of the base
system that generated this page is available @{link("BASE/cs_util/source.zip",
"here")} as a zip archive.

Please note that these terms apply only to the CAT-SOOP system itself and
not to any third-party software included with CAT-SOOP, nor to any course
material hosted on a CAT-SOOP instance, unless explicitly stated otherwise.

## Acknowledgements

* CAT-SOOP is written in the @{link("http://python.org", "Python")} programming language (v3.5).
* CAT-SOOP makes heavy use of @{link("http://jquery.com/", "jQuery")}.
* CAT-SOOP uses @{link("https://pypi.python.org/pypi/Markdown", "a Python implementation")} of John Gruber's @{link("http://daringfireball.net/projects/markdown/", "Markdown")} markup language.
* CAT-SOOP uses @{link("http://khan.github.io/KaTeX/", "KaTeX")} and @{link("http://www.mathjax.org/", "MathJax")} for rendering math in the browser.
* Expression questions use David Beazley's @{link("http://www.dabeaz.com/ply/", "Python Lex-Yacc")}.
* Python coding questions can optionally make use of the @{link("http://ace.ajax.org/#nav=about", "ACE")} code editor.
* CAT-SOOP's default theme uses @{link("http://getbootstrap.com", "Bootstrap")} and the following fonts: Montserrat by Julieta Ulanovsky, Lato by Lukasz Dziedzic, and Computer Modern Typewriter by Donald Knuth.


<python>
courses = csm_tutor.available_courses()
if len(courses) == 0:
    cs_print("There are currently no courses hosted on this system.")
else:
    cs_print("## Courses")
    cs_print("""
The following courses are hosted on this system:
""")
    for course_id,title in courses:
        cs_print('* [%s](BASE/%s/)' % (title, course_id))
</python>