```
\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_
```

# CAT-SOOP

[https://cat-soop.org](https://cat-soop.org)


## WHAT IS IT?

CAT-SOOP is a tool for automatic collection and assessment of online exercises,
originally developed primarily for use in MIT's 6.01 (Introduction to
Electrical Engineering and Computer Science via Robot Sensing, Software, and
Control).  It has since been used in several courses:

* MIT 6.01: Introduction to EECS via Robot Sensing, Software and Control
* MIT 6.02: Introduction to EECS via Communications Networks
* MIT 6.s08: Interconnected Embedded Systems
* MIT 6.s080: Brief Introduction to Computer Programming in Python
* MIT 6.003: Signals and Systems
* Olin College MTH 2132/SCI 2032: Bayesian Inference and Reasoning

No animals were harmed in the making of this CAT-SOOP.


## CAN I USE IT FOR MY COURSE?

Yes\*!  CAT-SOOP is [free/libre software](https://www.gnu.org/philosophy/free-sw.html),
available under the terms of the Soopycat License version 1
(see [LICENSE](https://gitlab.com/adqm/cat-soop/blob/master/LICENSE)
file for details).  Please note that the terms of this license apply only to the
CAT-SOOP system itself and any plugins in use, but not to any course material
hosted on a CAT-SOOP instance, unless explicitly stated otherwise.

The only requirements are [Python](https://www.python.org/) (v3.5+) and a web
server that supports either CGI or WSGI (e.g., [Apache HTTP
Server](https://httpd.apache.org/) or
[uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)+
[nginx](https://www.nginx.com/resources/wiki/)).

\*Assuming you can make it work.  Documentation is currently somewhat lacking
(read: totally nonexistent), but we are working on it...


## HOW DO I GET IT?

Development is carried out on Gitlab.com, so you can also clone the most
recent (potentially unstable) version with the following:
```
$ git clone https://gitlab.com/adqm/cat-soop.git
```

If you have SSH keys on Gitlab.com, you can clone instead with:
```
$ git clone git@gitlab.com:adqm/cat-soop.git
```


## IS IT ANY GOOD?

Yes.

## INCLUDED SOFTWARE

The following pieces of software are bundled with CAT-SOOP and are licensed
under their own terms:

* [Computer Modern Typewriter Font](http://checkmyworking.com/cm-web-fonts/)
    ([SIL Open Font License Verion 1.1](http://scripts.sil.org/cms/scripts/page.php?item_id=OFL_web))
    in `__MEDIA__/fonts/cmun*`
* [jQuery](http://jquery.com/) version 1.12.4
    ([MIT (Expat) License](https://jquery.org/license/))
    in `__MEDIA__/scripts/katex`
* [KaTeX](https://khan.github.io/KaTeX/) version 0.6.0
    ([MIT (Expat) License](https://github.com/Khan/KaTeX/blob/master/LICENSE.txt))
    in `__MEDIA__/scripts/katex`
* [Lato Font](http://www.latofonts.com/lato-free-fonts/)
    ([SIL Open Font License Verion 1.1](http://scripts.sil.org/cms/scripts/page.php?item_id=OFL_web))
    in `__MEDIA__/fonts/Lato*`
* [MathJax](https://www.mathjax.org/) version 2.6.1
    ([Apache License, version 2.0](https://github.com/mathjax/MathJax/blob/master/LICENSE))
    in `__MEDIA__/scripts/mathjax`
* [Montserrat Font](https://www.fontsquirrel.com/fonts/montserrat)
    ([SIL Open Font License Verion 1.1](http://scripts.sil.org/cms/scripts/page.php?item_id=OFL_web))
    in `__MEDIA__/fonts/Montserrat*`
* [Python Lex-Yacc](http://www.dabeaz.com/ply/) version 3.7
    ([BSD 3-Clause License](http://www.dabeaz.com/ply/README.txt))
    in `catsoop/tools/ply`
* [Python Markdown](https://pythonhosted.org/Markdown/) version 2.6.2
    ([BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause))
    in `catsoop/tools/markdown`
    
Modified versions of the following pieces of software are also included.  The
modified versions are available under the same terms as CAT-SOOP, and the
original versions are available under their own terms.

* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) version 4.4.1
    ([MIT (Expat) License](https://opensource.org/licenses/MIT))
    in `catsoop/tools/bs4`
    (locally modified to account for the structure of imports)
* [Bootstrap](http://getbootstrap.com/) version 3.3.6
    ([MIT (Expat) License](https://github.com/twbs/bootstrap/blob/master/LICENSE))
    in `__MEDIA__/scripts/bootstrap.js`
    (locally modified to include "callouts" from the Bootstrap web site)
* [highlight.js](https://highlightjs.org/) version 9.5.0
    ([BSD 3-Clause License](https://github.com/isagalaev/highlight.js/blob/master/LICENSE))
    in `__MEDIA__/scripts/highlight`
    (locally modified to change highlighting of Python code).
