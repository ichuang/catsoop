# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

import ast

implicit_multiplication = False


def parser(lex=None, yacc=None):
    tokens = ("PLUS",
              "MINUS",
              "TIMES",
              "DIVIDE",
              "EXP",
              "COMMA",
              "LPAREN",
              "RPAREN",
              "NAME",
              "NUMBER",
              "CARET",
              "LBRACKET",
              "RBRACKET", )

    t_ignore = " \t"

    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_EXP = r"\*\*"
    t_CARET = r"\^"
    t_COMMA = r","
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"

    t_NAME = r"[A-Za-z][A-Za-z0-9]*(_[A-Za-z0-9]*)?"
    t_NUMBER = r"((\d+\.\d*|\.\d+)([eE][-+]?\d+)?|\d+[eE][-+]?\d+|\d+)"

    lex.lex()

    precedence = (('left', 'PLUS', 'MINUS'),
                  ('left', 'TIMES', 'DIVIDE'),
                  ('left', 'EXP'),
                  ('right', 'UMINUS'), )

    def p_expression_binop(t):
        """
        expression : expression PLUS expression
                   | expression MINUS expression
                   | expression TIMES expression
                   | expression DIVIDE expression
                   | expression EXP expression
        """
        if t[2] == '**':
            t[2] = '^'
        t[0] = [t[2], t[1], t[3]]

    def p_expression_xor(t):
        """
        expression : expression CARET expression
        """
        t[0] = ['CALL', ['NAME', 'XOR'], [t[1], t[3]]]

    def p_expression_list(t):
        """
        expression : LBRACKET list_of_expressions RBRACKET
        """
        t[0] = ['LIST', t[2]]

    def p_expression_grouped(t):
        """
        expression : LPAREN expression RPAREN
        """
        t[0] = t[2]

    def p_expression_call(t):
        """
        expression : name LPAREN list_of_expressions RPAREN
        """
        t[0] = ['CALL', t[1], t[3]]

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
        t[0] = ['u-', t[2]]

    def p_expression_uplus(t):
        """
        expression : PLUS expression %prec UMINUS
        """
        t[0] = ['u+', t[2]]

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
        t[0] = ['NUMBER', complex(ast.literal_eval(t[1]), 0)]

    def p_name(t):
        """
        name : NAME
        """
        t[0] = ['NAME', t[1]]

    def p_empty(p):
        """
        empty :
        """
        pass

    return yacc.yacc(optimize=False, debug=False)
