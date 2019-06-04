<python>
cs_content_header = "CAT-SOOP v14.x Documentation"
</python>

<center>
<pre style="border-color:transparent; font-weight:bold; background-color:transparent;font-size:110%; color:inherit; line-height:1.1;display:inline-block;text-align:left;">
\
/    /\__/\
\__=(  o_O )=
(__________)
 |_ |_ |_ |_
</pre>
</center>


@{warning("""These docs are extremely sparse right now, and unfortunately, I have
trouble finding the time to sit down and write documentation.

If you have questions about using the software that aren't answered here,
please send an e-mail to `catsoop-users@mit.edu`; I'm happy to answer
questions, and I'll also try to work the result into the docs.

Better yet, if you have used CAT-SOOP and are interested in contributing
documentation, please see <a href="CURRENT/contributing">the section on
contributing documentation</a> for more information.

-Adam""")}

## Contents

<python>
for i in sorted(cs_children, key=lambda i: cs_children[i].get('cs_order', 1000)):
    if i == 'api':
        cs_print("* [API Documentation](CURRENT/api?p=catsoop)")
    else:
        cs_print("* [%s](CURRENT/%s)" % (cs_children[i].get('cs_long_name', i), i))
</python>
