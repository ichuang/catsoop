# This file is part of CAT-SOOP
# Copyright (c) 2011-2019 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
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

expression, _ = csm_tutor.question("expression")

defaults = dict(expression["defaults"])
defaults["csq_expressions"] = [("$x = ~$", ["2", "3"]), ("$y = ~$", ["sqrt(2)"])]
defaults["csq_combine_results"] = lambda results: sum(any(i) for i in results) / len(
    results
)

total_points = expression["total_points"]


def get_parsed_reps(submissions, **info):
    parser = expression["_get_parser"](info)
    funcs = dict(expression["default_funcs"])
    funcs.update(info.get("csq_funcs", {}))
    parsed = []
    for (ix, (prompt, solutions)) in enumerate(info["csq_expressions"]):
        osub = sub = submissions.get("__%s_%04d" % (info["csq_name"], ix), "")
        fprompt = csm_language.html_from_source(info, prompt)
        try:
            sub = parser.parse(sub)
            parsed.append(
                "%s<br/><displaymath>%s</displaymath>"
                % (fprompt, expression["tree2tex"](info, funcs, sub)[0])
            )
        except:
            parsed.append(
                '%s</br><center><font color="red">Error: could not parse your expression <code>%s</code></center></font>'
                % (fprompt, repr(osub))
            )
    msg = '<div class="question">Your expressions were parsed as:<hr/>'
    msg += "<hr />".join(parsed)
    return msg + "</div>"


checktext = "Check Syntax"


def handle_check(submissions, **info):
    return get_parsed_reps(submissions, **info)


def handle_submission(submissions, **info):
    results = []
    parsed = []

    for (ix, (prompt, solutions)) in enumerate(info["csq_expressions"]):
        sub = submissions.get("__%s_%04d" % (info["csq_name"], ix), "")

        # check each solution and save the results
        this_question = []
        if not isinstance(solutions, list):
            solutions = [solutions]
        for soln in solutions:
            spoof = dict(info)
            spoof["csq_soln"] = [soln]
            this_question.append(
                expression["handle_submission"]({info["csq_name"]: sub}, **spoof).get(
                    "score", 0.0
                )
            )

        results.append(this_question)

    msg = get_parsed_reps(submissions, **info)

    score = info["csq_combine_results"](results)
    if isinstance(score, (list, tuple)):
        score, extra_msg = score
        msg = "%s<hr/>%s" % (msg, extra_msg)

    return {"score": score, "msg": msg}


def escape(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")


def render_html(submissions, **info):
    submissions = submissions or {}
    out = '<table border="0">'
    for (ix, (prompt, _)) in enumerate(info["csq_expressions"]):
        qbox_name = "__%s_%04d" % (info["csq_name"], ix)
        out += '<tr><td align="right">'
        out += csm_language.html_from_source(info, prompt)
        out += "</td><td>"
        out += '<input type="text"'
        if info.get("csq_size", None) is not None:
            out += ' size="%s"' % info["csq_size"]

        out += ' value="%s"' % escape(submissions.get(qbox_name, ""))
        out += ' name="%s"' % qbox_name
        out += ' id="%s"' % qbox_name
        out += " /></td></tr>"
    return out + "</table>"


def answer_display(**info):
    custom_answer = info.get("csq_custom_answer_display", None)
    if custom_answer is not None:
        return custom_answer
    parser = expression["_get_parser"](info)
    out = ""
    funcs = dict(expression["default_funcs"])
    funcs.update(info.get("csq_funcs", {}))
    parsed = []
    for (ix, (prompt, solutions)) in enumerate(info["csq_expressions"]):
        fprompt = csm_language.html_from_source(info, prompt)
        if not isinstance(solutions, list):
            solutions = [solutions]
        for soln in solutions:
            try:
                soln = parser.parse(soln)
                parsed.append(
                    "%s<br/><displaymath>%s</displaymath>"
                    % (fprompt, expression["tree2tex"](info, funcs, soln)[0])
                )
            except:
                parsed.append(
                    '%s</br><center><font color="red">Error: could not parse expression <code>%s</code></center></font>'
                    % (fprompt, repr(soln))
                )
    return "<hr/>".join(parsed)
