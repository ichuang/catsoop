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

import os
import ast
import imp
import math
import cmath
import random
from collections import Sequence, defaultdict

numpy = None

def check_numpy():
    global numpy
    if numpy is not None:
        return True
    try:
        import numpy
        default_funcs.update({
            'transpose': (numpy.transpose, _render_transpose),
            'norm': (numpy.linalg.norm, _render_norm),
        })
        return True
    except:
        return False

def _render_transpose(x):
    return r'{%s}^T' % x[0]

def _render_norm(x):
    return r'\left\|{%s}\right\|' % x[0]

smallbox, _ = csm_tutor.question('smallbox')

defaults = {
    'csq_error_on_unknown_variable': False,
    'csq_input_check': lambda raw, tree: None,
    'csq_render_result': True,
    'csq_syntax': 'base',
    'csq_num_trials': 20,
    'csq_threshold': 1e-9,
    'csq_ratio_check': True,
    'csq_soln': ['6', 'sqrt(2)'],
    'csq_npoints': 1,
    'csq_msg_function': lambda sub: (''),
    'csq_show_check': False,
    'csq_variable_dimensions': {},
}

default_names = {'pi': [math.pi], 'e': [math.e], 'j': [1j], 'i': [1j]}


def _draw_sqrt(x):
    out = r"\sqrt{%s}" % (', '.join(x))
    if len(x) != 1:
        return out, "sqrt takes exactly one argument"
    return out


def _draw_abs(x):
    out = r"\left|%s\right|" % x[0]
    if len(x) != 1:
        return out, "abs takes exactly one argument"
    return out


def _draw_default(context, c):
    out = r"%s(%s)" % (c[1], ', '.join(c[2]))
    if len(c[2]) == 1 and _implicit_multiplication(context):
        return out, "Assuming implicit multiplication."
    else:
        return out, "Unknown function <tt>%s</tt>." % c[1]


def _default_func(context, names, funcs, c):
    if _implicit_multiplication(context):
        if len(c[2]) == 1:
            # implicit multiplication
            val1 = eval_expr(context, names, funcs, c[1])
            val2 = eval_expr(context, names, funcs, c[2][0])
            return val1 * val2
    return random.random()


def _draw_func(name):
    def _drawer(args):
        return r"%s\left(%s\right)" % (name, ', '.join(args))

    return _drawer


def _draw_log(x):
    if len(x) == 0:
        base = ''
    elif len(x) == 1:
        base = 'e'
    else:
        base = x[1]
    if any((i in x[0]) for i in ' -+'):
        arg = r'\left(%s\right)' % x[0]
    else:
        arg = x[0]
    out = r"\log_{%s}{%s}" % (base, arg)
    if len(x) > 2:
        return out, "log takes at most 2 arguments"
    return out


default_funcs = {
    'atan': (cmath.atan, _draw_func(r'\text{tan}^{-1}')),
    'asin': (cmath.asin, _draw_func(r'\text{sin}^{-1}')),
    'acos': (cmath.acos, _draw_func(r'\text{cos}^{-1}')),
    'tan': (cmath.tan, _draw_func(r'\text{tan}')),
    'sin': (cmath.sin, _draw_func(r'\text{sin}')),
    'cos': (cmath.cos, _draw_func(r'\text{cos}')),
    'log': (cmath.log, _draw_log),
    'sqrt': (cmath.sqrt, _draw_sqrt),
    'abs': (abs, _draw_abs),
    '_default': (_default_func, _draw_default)
}

def _contains(l, test):
    if not isinstance(l, list):
        return False
    elif l[0] == test:
        return True
    elif l[0] == 'CALL':
        return _contains(l[1], test) or any(_contains(i, test) for i in l[2])
    else:
        return any(_contains(i, test) for i in l[1:])


def eval_expr(context, names, funcs, n):
    return _eval_map[n[0]](context, names, funcs, n)


def eval_name(context, names, funcs, n):
    return names[n[1]]


def eval_number(context, names, funcs, n):
    return ast.literal_eval(n[1])


def eval_binop(func):
    def _evaler(context, names, funcs, o):
        left = eval_expr(context, names, funcs, o[1])
        right = eval_expr(context, names, funcs, o[2])
        return func(left, right)

    return _evaler


def eval_uminus(context, names, funcs, o):
    return -eval_expr(context, names, funcs, o[1])


def eval_uplus(context, names, funcs, o):
    return +eval_expr(context, names, funcs, o[1])


def eval_call(context, names, funcs, c):
    if c[1][0] == 'NAME' and c[1][1] in funcs:
        return funcs[c[1][1]][0](*(eval_expr(context, names, funcs, i)
                                   for i in c[2]))
    else:
        return funcs['_default'][0](context, names, funcs, c)


def _div(x, y):
    x = complex(float(x.real), float(x.imag))
    return x / y


_eval_map = {
    'NAME': eval_name,
    'NUMBER': eval_number,
    '+': eval_binop(lambda x, y: x + y),
    '-': eval_binop(lambda x, y: x - y),
    '*': eval_binop(lambda x, y: x * y),
    '/': eval_binop(_div),
    '@': eval_binop(lambda x, y: x @ y),
    '^': eval_binop(lambda x, y: x**y),
    'u-': eval_uminus,
    'u+': eval_uplus,
    'CALL': eval_call,
}


def _run_one_test(context, sub, soln, funcs, threshold, ratio=True):
    _sub_names = _get_all_names(sub)
    _sol_names = _get_all_names(soln)
    maps_to_try = _get_all_mappings(context, _sub_names, _sol_names)
    for m in maps_to_try:
        try:
            subm = eval_expr(context, m, funcs, sub)
        except:
            return False
        sol = eval_expr(context, m, funcs, soln)

        context['cs_debug'](subm, sol)

        mag = abs
        if check_numpy():
            subnum = isinstance(subm, numpy.ndarray)
            solnum = isinstance(sol, numpy.ndarray)
            if subnum and solnum:
                mag = numpy.linalg.norm
            elif subnum or solnum:
                return False
        scale_factor = sol if ratio else 1
        try:
            if mag(subm-sol) > mag(threshold*scale_factor):
                return False
        except:
            pass

    return True


def _get_all_names(tree):
    if not isinstance(tree, list):
        return []
    elif tree[0] == 'NAME':
        return [tree[1]]
    elif tree[0] == 'CALL':
        return _get_all_names(tree[1]) + sum((_get_all_names(i)
                                              for i in tree[2]), [])
    else:
        return sum((_get_all_names(i) for i in tree[1:]), [])


def _get_random_value():
    return random.uniform(1, 30)


def _get_all_mappings(context, soln_names, sub_names):
    names = dict(default_names)
    names.update(context.get('csq_names', {}))
    dimensions = context['csq_variable_dimensions']
    dim_vars = defaultdict(lambda: random.randint(2, 30))

    for n in soln_names:
        if n not in names:
            if n in dimensions:
                d = [i if isinstance(i, int) else dim_vars[i] for i in dimensions[n]]
                names[n] = numpy.random.rand(*d)
            else:
                names[n] = _get_random_value()

    for n in sub_names or []:
        if n not in names:
            if n in dimensions:
                d = [i if isinstance(i, int) else dim_vars[i] for i in dimensions[n]]
                names[n] = numpy.random.rand(*d)
            else:
                names[n] = _get_random_value()

    # map each name to a list of values to test
    for n in names:
        if callable(names[n]):
            names[n] = names[n]()
        if numpy is not None and isinstance(names[n], numpy.ndarray):
            names[n] = [names[n]]
        else:
            try:
                names[n] = [i for i in names[n]]
            except:
                names[n] = [names[n]]

    # get a list of dictionaries, each representing one mapping to test
    return _all_mappings_helper(names)


def _all_mappings_helper(m):
    lm = len(m)
    if lm == 0:
        return {}
    n = list(m.keys())[0]
    test = [{n: i} for i in m[n]]
    if lm == 1:
        return test
    c = dict(m)
    del c[n]
    o = _all_mappings_helper(c)
    out = []
    for i in o:
        for j in test:
            d = dict(i)
            d.update(j)
            out.append(d)
    return out


def total_points(**info):
    return info['csq_npoints']


def _get_syntax_module(context):
    syntax = context['csq_syntax']
    fname = os.path.join(context['cs_fs_root'], '__QTYPES__', 'expression',
                         '__SYNTAX__', '%s.py' % syntax)
    return imp.load_source(syntax, fname)


def _implicit_multiplication(context):
    m = _get_syntax_module(context)
    if hasattr(m, 'implicit_multiplication'):
        return m.implicit_multiplication
    else:
        return True


def _get_parser(context):
    return _get_syntax_module(context).parser(csm_tools.ply.lex, csm_tools.ply.yacc)


def handle_submission(submissions, **info):
    if len(info['csq_variable_dimensions']) > 0:
        assert check_numpy()

    _sub = sub = submissions[info['csq_name']]
    solns = info['csq_soln']

    parser = _get_parser(info)

    test_threshold = info['csq_threshold']

    funcs = dict(default_funcs)
    funcs.update(info.get('csq_funcs', {}))

    try:
        sub = parser.parse(sub)
    except:
        return {'score': 0.0, 'msg': '<font color="red">Error: '
                                     'could not parse input.</font>'}
    _m = None
    if sub is None:
        result = False
    else:
        in_check = info['csq_input_check'](_sub, sub)
        if in_check is not None:
            result = False
            _m = in_check
        else:
            if not isinstance(solns, list):
                solns = [solns]
            solns = [parser.parse(i) for i in solns]

            ratio = info['csq_ratio_check']
            result = False
            for soln in solns:
                for attempt in range(info['csq_num_trials']):
                    _sub_names = _get_all_names(sub)
                    _sol_names = _get_all_names(soln)
                    if info['csq_error_on_unknown_variable']:
                        _unique_names = set(_sub_names).difference(_sol_names)
                        if len(_unique_names) > 0:
                            _s = "s" if len(_unique_names) > 1 else ""
                            _v = ", ".join(tree2tex(info, funcs, ["NAME", i])[0]
                                           for i in _unique_names)
                            _m = "Unknown variable%s: $%s$" % (_s, _v)
                    result = _run_one_test(info, sub, soln, funcs, test_threshold, ratio)
                    if not result:
                        break
                if result:
                    break

    if info['csq_show_check']:
        if result:
            msg = '<img src="%s" />' % info['cs_check_image']
        else:
            msg = '<img src="%s" />' % info['cs_cross_image']
    else:
        msg = ''
    n = info['csq_name']
    msg += info['csq_msg_function'](submissions[info['csq_name']])
    msg = info['csm_language'].source_transform_string(info, msg)
    msg = ("""\n<script type="text/javascript">"""
           """$('#image%s').html(%r);</script>\n""") % (n, msg)
    if info['csq_render_result']:
        msg += get_display(info, n, sub, False, _m or '')
    else:
        msg += _m or ''
    return {'score': float(result), 'msg': msg}


checktext = "Check Syntax"


def handle_check(submission, **info):
    if len(info['csq_variable_dimensions']) > 0:
        assert check_numpy()
    last = submission.get(info['csq_name'])
    return get_display(info, info['csq_name'], last)


def render_html(last_log, **info):
    if len(info['csq_variable_dimensions']) > 0:
        if not check_numpy():
            return '<font color="red">Error: the <tt>numpy</tt> module is required for nonscalar values'
    name = info['csq_name']
    out = smallbox['render_html'](last_log, **info)
    out += "\n<span id='image%s'></span>" % (name, )
    return out


def get_display(info, name, last, reparse=True, extra_msg=''):
    try:
        if reparse:
            parser = _get_parser(info)
            tree = parser.parse(last)
        else:
            tree = last
        funcs = dict(default_funcs)
        funcs.update(info.get('csq_funcs', {}))
        last = '<displaymath>%s</displaymath>' % tree2tex(info, funcs, tree)[0]
    except:
        last = '<font color="red">ERROR: Could not interpret your input</font>'
    last += csm_language.source_transform_string(info, extra_msg)
    out = '<div id="expr%s">Your entry was parsed as:<br/>%s</div>' % (name,
                                                                       last)
    out += '<script type="text/javascript">catsoop.render_all_math($("#expr%s"), true)</script>' % name
    return out


def answer_display(**info):
    if len(info['csq_variable_dimensions']) > 0:
        if not check_numpy():
            return '<font color="red">Error: the <tt>numpy</tt> module is required for nonscalar values'
    parser = _get_parser(info)
    funcs = dict(default_funcs)
    funcs.update(info.get('csq_funcs', {}))
    if isinstance(info['csq_soln'], str):
        a = tree2tex(info, funcs, parser.parse(info['csq_soln']))[0]
        out = ("<p>Solution: <tt>%s</tt><br>"
               "<div id=\"%s_soln\"><displaymath>%s</displaymath></div>"
               "<p>") % (info['csq_soln'], info['csq_name'], a)
    else:
        out = ("<p><div id=\"%s_soln\">"
               "<b>Multiple Possible Solutions:</b>") % info['csq_name']
        count = 1
        for i in info['csq_soln']:
            out += '<hr width="80%" />'
            a = tree2tex(info, funcs, parser.parse(i))[0]
            out += ('<p>Solution %s: <tt>%s</tt><br>'
                    '<displaymath>%s</displaymath></p>') % (count, i, a)
            count += 1
        out += '</div>'
    out += '<script type="text/javascript">catsoop.render_all_math($("#expr%s"), true)</script>' % info[
        'csq_name']
    return out

# LaTeX Conversion

GREEK_LETTERS = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta',
                 'theta', 'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi',
                 'omicron', 'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi',
                 'chi', 'psi', 'omega']
GREEK_DICT = {}
for i in GREEK_LETTERS:
    GREEK_DICT[i] = "\\%s" % i
    GREEK_DICT[i.upper()] = "\\%s" % i.title()


def name2tex(context, funcs, n):
    prec = 5
    on = n = n[1]
    s = None
    if '_' in n:
        n, s = n.split('_')
    if n in GREEK_DICT:
        n = GREEK_DICT[n]
    if on in context['csq_variable_dimensions']:
        n = r'\mathbf{%s}' % n
    if s is not None:
        if s in GREEK_DICT:
            s = GREEK_DICT[s]
        return ('%s_{%s}' % (n, s)), prec
    return n, prec


def plus2tex(context, funcs, n):
    prec = 1
    left, lprec = tree2tex(context, funcs, n[1])
    right, rprec = tree2tex(context, funcs, n[2])
    return "%s + %s" % (left, right), prec


def minus2tex(context, funcs, n):
    prec = 1
    left, lprec = tree2tex(context, funcs, n[1])
    right, rprec = tree2tex(context, funcs, n[2])
    if rprec <= prec:
        right = r"\left(%s\right)" % right
    return "%s - %s" % (left, right), prec


def div2tex(context, funcs, n):
    prec = 2
    left, lprec = tree2tex(context, funcs, n[1])
    right, rprec = tree2tex(context, funcs, n[2])
    return (r"\frac{%s}{%s}" % (left, right)), prec


def times2tex(context, funcs, n):
    prec = 2
    left, lprec = tree2tex(context, funcs, n[1])
    if lprec < prec:
        left = r"\left(%s\right)" % left
    right, rprec = tree2tex(context, funcs, n[2])
    if rprec < prec:
        right = r"\left(%s\right)" % right
    return r"%s \cdot %s" % (left, right), prec


def matmul2tex(context, funcs, n):
    prec = 2
    left, lprec = tree2tex(context, funcs, n[1])
    if lprec < prec:
        left = r"\left(%s\right)" % left
    right, rprec = tree2tex(context, funcs, n[2])
    if rprec < prec:
        right = r"\left(%s\right)" % right
    return r"%s%s" % (left, right), prec


def exp2tex(context, funcs, n):
    prec = 4
    left, lprec = tree2tex(context, funcs, n[1])
    if lprec <= prec:
        left = r"\left(%s\right)" % left
    right, rprec = tree2tex(context, funcs, n[2])
    return (r"%s ^ {%s}" % (left, right)), prec


def uminus2tex(context, funcs, n):
    prec = 3
    operand, oprec = tree2tex(context, funcs, n[1])
    if oprec < prec:
        operand = r"\left(%s\right)" % operand
    return "-%s" % operand, prec


def uplus2tex(context, funcs, n):
    prec = 3
    operand, oprec = tree2tex(context, funcs, n[1])
    if oprec < prec:
        operand = r"\left(%s\right)" % operand
    return "+%s" % operand, prec


def call2tex(context, funcs, c):
    prec = 6
    if c[1][0] == 'NAME' and c[1][1] in funcs:
        o = funcs[c[1][1]][1]([tree2tex(context, funcs, i)[0] for i in c[2]])
    else:
        new_c = list(c)
        new_c[1] = tree2tex(context, funcs, c[1])[0]
        new_c[2] = [tree2tex(context, funcs, i)[0] for i in c[2]]
        o = funcs['_default'][1](context, new_c)
    if isinstance(o, str):
        pass
    elif isinstance(o, Sequence) and len(o) > 1:
        o = r"{\color{red} \underbrace{%s}_{\text{%s}}}" % tuple(o[:2])
    return o, prec


def _opt_clear_dec_part(x):
    n = x.split('.', 1)
    if len(n) == 1 or all(i == '0' for i in n[1]):
        return n[0]
    return '.'.join(n)


def number2tex(context, funcs, x):
    n = x[1].lower()
    if 'e' in n:
        return (r'%s\cdot 10^{%s}' % tuple(n.split('e')), 22)
    return x[1], 5


_tree_map = {
    'NAME': name2tex,
    'NUMBER': number2tex,
    '+': plus2tex,
    '-': minus2tex,
    '*': times2tex,
    '/': div2tex,
    '^': exp2tex,
    '@': matmul2tex,
    'u-': uminus2tex,
    'u+': uplus2tex,
    'CALL': call2tex,
}


def tree2tex(context, funcs, tree):
    return _tree_map[tree[0]](context, funcs, tree)
