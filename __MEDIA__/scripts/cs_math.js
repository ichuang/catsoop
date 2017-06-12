/* This file is part of CAT-SOOP
 * Copyright (c) 2011-2017 Adam Hartz <hartz@mit.edu>
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
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// Math rendering for CAT-SOOP
// Expects jQuery, KaTeX, and MathJax to be loaded already

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
    elt = $(elt);
    var tex = elt.text(); // TeX Source
    var display = elt.hasClass('cs_displaymath');
    try{
        katex.render(tex, elt.get(0), {displayMode: display});
    }catch(err){
        if(display){
            var b = "\\[";
            var e = "\\]";
        }else{
            var b = "\\(";
            var e = "\\)";
        }
        elt.text(b + tex + e);
        if(render_now){
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, elt[0]]);
        }
    }
    elt.removeClass('cs_math_to_render');
}

// render all math elements within a given DOM element
catsoop.render_all_math = function (elt, immediate){
    immediate = typeof immediate !== 'undefined' ? immediate : false;
    $('.cs_math_to_render', $(elt)).each(function(){
            var elt = $(this);
            catsoop.render_math(elt, immediate);
    }).promise().done(function(){
        if(!immediate){
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, elt]);
        }
    });
}

// when the page loads, render all math elements on the page
$(document).ready(function(){{catsoop.render_all_math(document)}});
