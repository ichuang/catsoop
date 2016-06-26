// This file is part of CAT-SOOP
// Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
// CAT-SOOP is free software, licensed under the terms described in the LICENSE
// file.  If you did not receive a copy of this file with CAT-SOOP, please see:
// https://cat-soop.org/LICENSE

// Math rendering for CAT-SOOP
// Expects jQuery, KaTeX, and MathJax to be loaded already

// configure MathJax not to typeset on startup
MathJax.Hub.Config({skipStartupTypeset:true,
                    imageFont: null,
                    MathMenu: { showLocale: false, showRenderer: false },
                    TeX: { extensions: ["color.js"] }});

// render math
// try to render with katex (fast, but limited support), and
// fall back to mathjax (slow, but good support) if necessary
function cs_render_math(elt, render_now) {
    render_now = typeof render_now !== 'undefined' ? render_now : false;
    elt = $(elt);
    var tex = elt.text(); // TeX Source
    var type = elt.prop("tagName");
    var disp = false;
    var thisId = elt.attr("id");
    if(type=="DIV"){
        disp = true;
    }
    try{
        katex.render(tex, elt.get(0), {displayMode: Boolean(disp)});
    }catch(err){
        if(disp){
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
    elt.attr("id", "cs_rendered_" + thisId);
}

// render all math elements within a given DOM element
function cs_render_all_math(elt, immediate){
    immediate = typeof immediate !== 'undefined' ? immediate : false;
    $('[id^="cs_math"]', $(elt)).each(function(){
            cs_render_math($(this), immediate);
    }).promise().done(function(){
        if(!immediate){
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, elt]);
        }
    });
}

// when the page loads, render all math elements on the page
$(document).ready(function(){{cs_render_all_math(document)}});
