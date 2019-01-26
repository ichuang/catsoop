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

import json
import collections.abc


def js_files(context):
    return ["_qtype/circuit/schematic.js"]


defaults = {
    "csq_soln": "{}",
    "csq_check_function": lambda sub, soln: sub["circuit"] == soln["circuit"],
    "csq_npoints": 1,
    "csq_msg_function": lambda sub, soln: "",
    "csq_show_check": True,
    "csq_show_analyses": [],  # can contain 'dc', 'ac', 'tran'
    "csq_check_analyses": {"dc": True},
    "csq_parts": "all",
    "csq_ac_name": "input",
    "csq_ac_lofreq": "10",
    "csq_ac_hifreq": "1G",
    "csq_ac_npts": "100",
    "csq_tran_npts": "100",
    "csq_tran_tstop": "1",
}

ANALYSES = ["dc", "ac", "tran"]

PARTS_MAP = {
    "ground": "g",
    "gnd": "g",
    "g": "g",
    "label": "b",
    "b": "b",
    "voltage": "v",
    "vsrc": "v",
    "voltage source": "v",
    "v": "v",
    "current": "i",
    "isrc": "i",
    "current source": "i",
    "i": "i",
    "resistor": "r",
    "r": "r",
    "capacitor": "c",
    "c": "c",
    "inductor": "l",
    "l": "l",
    "opamp": "o",
    "o": "o",
    "diode": "d",
    "d": "d",
    "nfet": "n",
    "n": "n",
    "pfet": "p",
    "p": "p",
    "probe": "s",
    "s": "s",
    "vprobe": "s",
    "ammeter": "a",
    "iprobe": "a",
    "a": "a",
}

PARTS_NAME_MAP = {
    "g": "ground",
    "r": "resistor",
    "v": "vsrc",
    "i": "isrc",
    "c": "capacitor",
    "l": "inductor",
    "o": "opamp",
    "d": "diode",
    "n": "nfet",
    "p": "pfet",
}


def parse_analyses(anlist):
    if anlist == "all":
        return ANALYSES
    else:
        return list(filter(lambda x: x in ANALYSES, map(lambda x: x.lower(), anlist)))


def parse_parts(partlist):
    if partlist == "all":
        return list(set(PARTS_MAP.values()))
    out = set()
    for i in partlist:
        out.add(PARTS_MAP.get(i.lower(), None))
    out.discard(None)
    return list(out)


def create_check_rep(x, info):
    if isinstance(x, dict) and all(
        i in x for i in {"circuit", "results", "vprobes", "iprobes"}
    ):
        return x
    out = {"circuit": [], "results": {}, "vprobes": {}, "iprobes": {}}
    results_keys = {"dc", "ac", "transient"}
    for i in x:
        if i[0] in results_keys and i[0] in info["csq_check_analyses"]:
            out["results"][i[0]] = i[1]
        elif i[0] == "s":
            out["vprobes"][str(i[2]["_json_"])] = i[-1][0]
        elif i[0] == "a":
            out["iprobes"][str(i[2]["_json_"])] = i[-1]
        elif i[0] == "view":
            continue
        elif i[0] in PARTS_NAME_MAP:
            values = {k: v for k, v in i[2].items() if k != "_json_"}
            values["type"] = PARTS_NAME_MAP[i[0]]
            values["nodes"] = i[-1]
            values["name"] = str(i[2]["_json_"])
            out["circuit"].append(values)
    return out


def escape(s):
    return s.replace('"', "&quot;")


def total_points(**info):
    return info["csq_npoints"]


def handle_submission(submissions, **info):
    check = info["csq_check_function"]
    sub = create_check_rep(json.loads(submissions[info["csq_name"]]), info)
    soln = info["csq_soln"]
    check_result = check(sub, soln)
    if isinstance(check_result, collections.abc.Mapping):
        score = check_result["score"]
        msg = check_result["msg"]
    elif isinstance(check_result, collections.abc.Sequence):
        score, msg = check_result
    else:
        score = check_result
        mfunc = info["csq_msg_function"]
        try:
            msg = mfunc(sub, soln)
        except:
            try:
                msg = mfunc(sub)
            except:
                msg = ""
    percent = float(score)
    if info["csq_show_check"]:
        if percent == 1.0:
            response = '<img src="%s" />' % info["cs_check_image"]
        elif percent == 0.0:
            response = '<img src="%s" />' % info["cs_cross_image"]
        else:
            response = ""
    else:
        response = ""
    response += msg
    return {"score": percent, "msg": response}


def render_html(last_log, **info):
    last_log = last_log or {}
    name = info["csq_name"]
    init = last_log.get(name, info.get("csq_initial", "[]"))
    out = '<input type="hidden" class="schematic"'
    out += ' parts="%s"' % ",".join(parse_parts(info["csq_parts"]))
    out += ' analyses="%s"' % ",".join(parse_analyses(info["csq_show_analyses"]))
    out += ' submit_analyses="%s"' % escape(
        json.dumps({k: True for k in info["csq_check_analyses"]})
    )
    if "ac" in info["csq_check_analyses"]:
        out += " ac_name=%r" % info["csq_ac_name"]
        out += " ac_lo=%s" % repr(info["csq_ac_lofreq"])
        out += " ac_hi=%s" % repr(info["csq_ac_hifreq"])
        out += " ac_npts=%s" % repr(info["csq_ac_npts"])
    if "tran" in info["csq_check_analyses"]:
        out += " tran_npts=%s" % repr(info["csq_tran_npts"])
        out += " tran_tstop=%s" % repr(info["csq_tran_tstop"])
    out += ' value="%s"' % escape(init)
    out += ' name="%s"' % name
    out += ' id="%s"/>' % name
    return out + (
        '\n<script type="text/javascript">'
        "\n// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3"
        "update_schematics();"
        'document.addEventListener("DOMContentLoaded", function(){'
        'document.getElementById("%s_buttons").addEventListener("mouseover", function(){'
        'document.getElementById("%s").schematic.prepare_submission();'
        "\n// @license-end"
        "});"
        "});"
        "</script>"
    ) % (name, name)


def answer_display(**info):
    out = "Solution: %s" % (info["csq_soln"])
    return out
