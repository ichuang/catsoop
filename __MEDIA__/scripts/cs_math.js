/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Affero General Public License as published by the
 * Free Software Foundation, either version 3 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License
 * for more details.
 *
 * As an additional permission under GNU AGPL version 3 section 7, you may
 * distribute non-source (e.g., minimized or compacted) forms of that code
 * without the copy of the GNU AGPL normally required by section 4, provided
 * you include this license notice and a URL through which recipients can
 * access the Corresponding Source.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// Math rendering for CAT-SOOP
// Expects KaTeX, and MathJax to be loaded already

// configure MathJax not to typeset on startup
MathJax.Hub.Config({skipStartupTypeset:true,
                    imageFont: null,
                    MathMenu: { showLocale: false, showRenderer: false },
                    TeX: { extensions: ["color.js", "[a11y]/accessibility-menu.js"] }});

// render math
// try to render with katex (fast, but limited support), and
// fall back to mathjax (slow, but good support) if necessary
catsoop.render_math = function (elt, render_now) {
    render_now = typeof render_now !== 'undefined' ? render_now : false;
    var tex = elt.innerText; // TeX Source
    var display = elt.classList.contains('cs_displaymath');
    var need_mathjax = false;
    try{
        katex.render(tex, elt, {displayMode: display});
    }catch(err){
        if(display){
            var b = "\\[";
            var e = "\\]";
        }else{
            var b = "\\(";
            var e = "\\)";
        }
        elt.innerText = b + tex + e;
        need_mathjax = true;
        if(render_now){
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, elt[0]]);
        }
    }
    elt.classList.remove('cs_math_to_render');
    return need_mathjax;
}

// render all math elements within a given DOM element
catsoop.render_all_math = function (elt, immediate){
    immediate = typeof immediate !== 'undefined' ? immediate : false;
    var mathelts = elt.getElementsByClassName('cs_math_to_render');
    var need_mathjax = false;
    while(mathelts.length > 0){
        need_mathjax |= catsoop.render_math(mathelts[0], immediate);
    }
    if(need_mathjax && !immediate){
        MathJax.Hub.Queue(["Typeset", MathJax.Hub, elt]);
    }
}

// when the page loads, render all math elements on the page
document.addEventListener("DOMContentLoaded", function(event) {
      catsoop.render_all_math(document);
});
