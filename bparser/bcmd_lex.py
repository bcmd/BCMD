#!/usr/bin/python
#
# lexical analysis rules for bcmd's model description language
#

import sys
import decimal

if sys.version_info[0] >= 3:
    raw_input = input

## LEX ---------------------------------

tokens = (
    'ID','NUMBER',
    
    # newlines terminate statements unless followed by indents
    'NEWINDENT', 'END',
    
    # doc comments may eventually be useful, ordinary comments are discarded 
    'DOC','COMMENT',
    
    # Standard operators (+,-,*,/, ^, <, <=, >, >=, ==, !=)
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER',
    'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',
    
    # Non-standard operators (->, <->, =, :=, ~, ')
    'ARROW', 'DARROW', 'EQUALS', 'INIT', 'TILDE', 'PRIME',
    
    # Conditional operator
    'CONDOP',
    
    # Delimiters ( ) { } [ ] , :
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'LBRACKET', 'RBRACKET', 'COMMA', 'COLON',
    
    # Optional naming for equations etc
    'LABEL',
    
    # Direct C code embedding [**  **]
    'EMBEDDED',
    
    # Compiler directives
    'IMPORT', 'VERSION', 'INDEPENDENT', 'OUTPUT', 'INPUT', 'EXTERN'
    )

# Tokens

t_ID = r'[a-zA-Z_][a-zA-Z0-9_]*'

def t_EMBEDDED(t):
    r'\[\*\*(((?!(\*\*\]))[\s\S\n])*)\*\*\]'
    t.value = t.value[3:-3].strip()
    return t

def t_IMPORT(t):
    r'@import'
    return t

def t_VERSION(t):
    r'@version'
    return t

def t_INDEPENDENT(t):
    r'@independent'
    return t

def t_OUTPUT(t):
    r'@output'
    return t

def t_INPUT(t):
    r'@input'
    return t

def t_EXTERN(t):
    r'@extern'
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?([eE][-+]?\d+)?'
    t.value = decimal.Decimal(t.value)
    return t

def t_DOC(t):
    r'\043\043[^\n]*'
    return t

def t_COMMENT(t):
    r'[ ]*\043[^\n]*'  # \043 is '#'
    pass

def t_LABEL(t):
    r'"[^"\n]+"'
    t.value = t.value[1:-1].strip()
    return t

def t_NEWINDENT(t):
    r'\n[ \t]+'
    t.lexer.lineno += 1
    pass
    
def t_END(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    return t

t_PLUS             = r'\+'
t_MINUS            = r'-'
t_TIMES            = r'\*'
t_DIVIDE           = r'/'
t_POWER            = r'\^'
t_LT               = r'<'
t_GT               = r'>'
t_LE               = r'<='
t_GE               = r'>='
t_EQ               = r'=='
t_NE               = r'!='

t_INIT             = r':='
t_ARROW            = r'->'
t_DARROW           = r'<->'
t_EQUALS           = r'='
t_TILDE            = r'~'
t_PRIME            = r'\''

t_CONDOP           = r'\?'

# Delimiters
t_LPAREN           = r'\('
t_RPAREN           = r'\)'
t_LBRACE           = r'\{'
t_RBRACE           = r'\}'
t_LBRACKET         = r'\['
t_RBRACKET         = r'\]'
t_COMMA            = r','
t_COLON            = r':'

def t_WS(t):
    r'[ \t]+'
    pass

# unrecognised characters are simply dropped -- this means
# that some syntax errors might get automagically "fixed"
def t_error(t):
    print >> sys.stderr, "Ignoring illegal character '%s'" % t.value[0]
    t.lexer.skip(1)
    

# run this file directly to just test lexer
if __name__ == '__main__':
     import ply.lex as lex
     lex.lex()
     lex.runmain()

