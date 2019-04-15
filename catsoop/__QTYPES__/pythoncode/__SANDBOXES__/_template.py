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

import sys
import time


class OpcodeLimitReached(Exception):
    pass


RESULT_AS_STRING = %(result_as_string)r

OPCODE_TRACING_ENABLED = sys.version_info > (3, 7) and %(enable_opcode_count)s
if OPCODE_TRACING_ENABLED:

    def trace_closure(limit=float("inf")):
        executed_opcodes = 0
        limit_reached = False

        def tracer(frame, event, arg):
            nonlocal executed_opcodes, limit_reached
            frame.f_trace_opcodes = True
            if event == "opcode":
                executed_opcodes += 1
                if executed_opcodes >= limit:
                    limit_reached = True
                    raise OpcodeLimitReached
            return tracer

        def get():
            return executed_opcodes

        def killed():
            return limit_reached

        names = {"tracer": tracer, "get": get, "killed": killed}

        return lambda n: names[n]

    inf = float("inf")
    tracer = trace_closure(limit=%(opcode_limit)r)
    sys.settrace(tracer("tracer"))


class NoAnswerGiven:
    pass


results = {}
start_time = time.time()
try:
    import %(test_module)s as test_module

    ans = getattr(test_module, "_catsoop_answer", NoAnswerGiven)
    if ans is not NoAnswerGiven:  # we got a result back
        if RESULT_AS_STRING:
            ans = repr(ans)
        results["result"] = ans
    results["duration"] = time.time() - start_time
    results["complete"] = True
except OpcodeLimitReached:
    pass
except Exception as e:
    results["exception_type"] = e.__class__.__name__
    results["exception_args"] = e.args
    raise
finally:
    if OPCODE_TRACING_ENABLED:
        results["opcode_count"] = tracer("get")()
        results["opcode_limit_reached"] = tracer("killed")()
    print("---")
    print(results)
