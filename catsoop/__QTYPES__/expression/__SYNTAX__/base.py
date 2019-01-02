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

import ast


def parser(lex=None, yacc=None):
    tokens = (
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "EXP",
        "COMMA",
        "LPAREN",
        "RPAREN",
        "NAME",
        "NUMBER",
    )

    t_ignore = " \t"

    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_EXP = r"\^"
    t_COMMA = r","
    t_LPAREN = r"\("
    t_RPAREN = r"\)"

    t_NAME = r"[A-Za-z][A-Za-z0-9]*(_[A-Za-z0-9]*)?"
    t_NUMBER = r"((\d+\.\d*|\.\d+)([eE][-+]?\d+)?|\d+[eE][-+]?\d+|\d+)[jJ]?"

    lex.lex()

    precedence = (
        ("left", "PLUS", "MINUS"),
        ("left", "TIMES", "DIVIDE"),
        ("right", "UMINUS"),
        ("right", "EXP"),
    )

    def p_expression_binop(t):
        """
        expression : expression PLUS expression
                   | expression MINUS expression
                   | expression TIMES expression
                   | expression DIVIDE expression
                   | expression EXP expression
                   | number name EXP expression
                   | number name
        """
        if len(t) == 4:
            t[0] = [t[2], t[1], t[3]]
        elif len(t) == 5:
            t[0] = ["*", t[1], ["^", t[2], t[4]]]
        else:
            t[0] = ["*", t[1], t[2]]

    def p_expression_grouped(t):
        """
        expression : LPAREN expression RPAREN
        """
        t[0] = t[2]

    def p_expression_call(t):
        """
        expression : name LPAREN list_of_expressions RPAREN
        """
        t[0] = ["CALL", t[1], t[3]]

    def p_expression_impmul(t):
        """
        expression : LPAREN expression RPAREN LPAREN expression RPAREN
                   | number LPAREN expression RPAREN
        """
        if len(t) == 5:
            t[0] = ["*", t[1], t[3]]
        else:
            t[0] = ["*", t[2], t[5]]

    def p_list_of_expressions(t):
        """
        list_of_expressions : empty
                            | expression COMMA list_of_expressions
                            | expression opt_comma
        """
        if len(t) == 4:
            t[0] = [t[1]] + t[3]
        elif len(t) == 3:
            t[0] = [t[1]]
        else:
            t[0] = []

    def p_opt_comma(t):
        """
        opt_comma : empty
                  | COMMA
        """
        pass

    def p_expression_uminus(t):
        """
        expression : MINUS expression %prec UMINUS
        """
        t[0] = ["u-", t[2]]

    def p_expression_atom(t):
        """
        expression : number
                   | name
        """
        t[0] = t[1]

    def p_number(t):
        """
        number : NUMBER
        """
        t[0] = ["NUMBER", t[1]]

    def p_name(t):
        """
        name : NAME
        """
        t[0] = ["NAME", t[1]]

    def p_empty(p):
        """
        empty :
        """
        pass

    return yacc.yacc(optimize=False, debug=False, write_tables=False)
