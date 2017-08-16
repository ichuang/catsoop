<python>
# This file is part of CAT-SOOP
# Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
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

def link(url, text=None):
    text = text or url
    return '<a href="%s" target="_blank">%s</a>' % (url, text)
</python>

<pre class="catsooplogo">
\            
/    /\__/\  
\__=(  o_O )=
(__________) 
 |_ |_ |_ |_ 
</pre>

<center>
@{link("https://catsoop.mit.edu")}
</center>

<python>
if cs_main_page_text:
    print(cs_main_page_text)
</python>

## About CAT-SOOP

CAT-SOOP is a tool for automatic collection and assessment of online exercises.
CAT-SOOP is @{link("https://www.fsf.org/about/what-is-free-software", "free software")},
available under the terms of the
@{link("BASE/cs_util/license", "GNU Affero General Public License, version 3+")}.
In accordance with the terms of this license, the source code of the base
system that generated this page is available @{link("BASE/cs_util/source.zip",
"here")} as a zip archive.

Please note that these terms apply only to the CAT-SOOP system itself and
not to any third-party software included with CAT-SOOP, nor to any course
material hosted on a CAT-SOOP instance, unless explicitly stated otherwise.

## Courses

<python>
courses = csm_tutor.available_courses()
if len(courses) == 0:
    print("There are currently no courses hosted on this system.")
else:
    print("""
The following courses are hosted on this system:
""")
    for course_id, title in courses:
        title = title.replace('<br>', ' ').replace('<br/>', ' ').replace('</br>', ' ').replace('<br />', ' ')
        if title == course_id:
            print('* [%s](BASE/%s/)' % (course_id, course_id))
        else:
            print('* [%s](BASE/%s/): %s' % (course_id, course_id, title))
</python>
