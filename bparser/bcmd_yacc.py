#!/usr/bin/python
#
# prototype parser for bcmd's model description language
#

import sys
import decimal

if sys.version_info[0] >= 3:
    raw_input = input

import ply.lex as lex
import ply.yacc as yacc
import bcmd_lex

from bcmd_lex import tokens

precedence = (
        ('nonassoc', 'WEAKEST'),
        ('right', 'END'),
        ('right', 'COLON'),
        ('right', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
	('left', 'PLUS', 'MINUS'),
	('left', 'TIMES', 'DIVIDE'),
	('left', 'POWER'),
	('right', 'UMINUS'),
)

# grammar rules

def p_model_items(p):
    'model : items'
    p[0] = p[1]

def p_items_single(p):
    'items : item'
    p[0] = (p[1],)

def p_items_items_append(p):
    'items : items item'
    p[0] = p[1] + (p[2],)

def p_preceded_items(p):
    'items : end items %prec WEAKEST'
    p[0] = p[2]

def p_end(p):
    '''end : END
           | END end'''
    p[0] = p[1]

def p_item_nonterminal(p):
    '''item : reaction
            | algeqn
            | diffeqn
            | assign
            | constraint
            | imports
            | version
            | outputs
            | inputs
            | externs
            | independent'''
    p[0] = p[1]

def p_item_DOC(p):
    'item : DOC end'
    p[0] = ('DOC', p[1].strip('# \n\r\t') )

def p_item_EMBEDDED(p):
    'item : EMBEDDED end'
    p[0] = ('EMBEDDED', p[1])

def p_imports(p):
    'imports : import end'
    p[0] = p[1]
    
def p_import_single(p):
    'import : IMPORT ID'
    p[0] = ('import', p[2])

def p_import_append(p):
    'import : import ID'
    p[0] = p[1] + (p[2],)

def p_version(p):
    '''version : VERSION ID end
               | VERSION LABEL end
               | VERSION NUMBER end'''
    p[0] = ('version', str(p[2]))

def p_independent(p):
    'independent : INDEPENDENT ID end'
    p[0] = ('independent', p[2])

def p_outputs(p):
    'outputs : output end'
    p[0] = p[1]
    
def p_output_single(p):
    'output : OUTPUT ID'
    p[0] = ('output', p[2])

def p_output_append(p):
    'output : output ID'
    p[0] = p[1] + (p[2],)

def p_inputs(p):
    'inputs : input end'
    p[0] = p[1]
    
def p_input_single(p):
    'input : INPUT ID'
    p[0] = ('input', p[2])

def p_input_append(p):
    'input : input ID'
    p[0] = p[1] + (p[2],)

def p_externs(p):
    'externs : extern end'
    p[0] = p[1]
    
def p_extern_single(p):
    'extern : EXTERN ID'
    p[0] = ('extern', p[2])

def p_extern_append(p):
    'extern : extern ID'
    p[0] = p[1] + (p[2],)

def p_reaction_supply(p):
    'reaction : ARROW chemterm rateterm label end'
    p[0] = ('reaction', 'influx', p[4], p[2], p[3])

def p_reaction_deplete(p):
    'reaction : chemterm ARROW rateterm label end'
    p[0] = ('reaction', 'outflux', p[4], p[1], p[3])

def p_reaction_oneway(p):
    'reaction : chemterm ARROW chemterm rateterm label end'
    p[0] = ('reaction', 'oneway', p[5], p[1], p[3], p[4])

def p_reaction_twoway(p):
    'reaction : chemterm DARROW chemterm rateterm rateterm label end'
    p[0] = ('reaction', 'twoway', p[6], p[1], p[3], p[4], p[5])

def p_chemical(p):
    'chemical : LBRACKET ID RBRACKET'
    p[0] = ('chemical', p[2])

def p_chemical_compartment(p):
    'chemical : LBRACKET ID COMMA ID RBRACKET'
    p[0] = ('chemical', p[2], p[4])

def p_chemterm_default(p):
    'chemterm : chemical'
    p[0] = ('chemterm', ('mathterm', decimal.Decimal(1)), p[1])

def p_chemterm_quant(p):
    'chemterm : mathterm chemical'
    p[0] = ('chemterm', p[1], p[2])

def p_chemterm_default_append(p):
    'chemterm : chemterm PLUS chemical'
    p[0] = p[1] + (('mathterm', decimal.Decimal(1)), p[3])

def p_chemterm_quant_append(p):
    'chemterm : chemterm PLUS mathterm chemical'
    p[0] = p[1] + (p[3], p[4])

def p_logterm(p):
    '''logterm : mathterm EQ mathterm
               | mathterm NE mathterm
               | mathterm LT mathterm
               | mathterm LE mathterm
               | mathterm GT mathterm
               | mathterm GE mathterm'''
    p[0] = ('logical', p[2], p[1], p[3])

def p_logterm_paren(p):
    'logterm : LPAREN logterm RPAREN'
    p[0] = p[2]

def p_condterm(p):
    'condterm : logterm CONDOP mathterm COLON mathterm'
    p[0] = ('conditional', p[1], p[3], p[5])

def p_binop(p):
    '''binop : mathterm PLUS mathterm
             | mathterm MINUS mathterm
             | mathterm TIMES mathterm
             | mathterm DIVIDE mathterm
             | mathterm POWER mathterm'''
    p[0] = ('arithmetic', p[2], p[1], p[3])

def p_mathterm_single(p):
    '''mathterm : NUMBER
                | ID
                | func
                | binop
                | condterm'''
    p[0] = ('mathterm', p[1])

def p_mathterm_paren(p):
    'mathterm : LPAREN mathterm RPAREN'
    p[0] = p[2]

def p_mathterm_uminus(p):
    'mathterm : MINUS mathterm %prec UMINUS'
    # this may not be a reasonable way to do this, but we shall see
    p[0] = ('mathterm', ('arithmetic', '*', ('mathterm', decimal.Decimal(-1)), p[2]))

def p_arglist_single(p):
    'arglist : mathterm'
    p[0] = ('arglist', p[1])

def p_arglist_append(p):
    'arglist : arglist COMMA mathterm'
    p[0] = p[1] + (p[3],)

def p_func_noargs(p):
    'func : ID LPAREN RPAREN'
    p[0] = ('function', p[1], ())

def p_func_args(p):
    'func : ID LPAREN arglist RPAREN'
    p[0] = ('function', p[1], p[3])

def p_algeqn(p):
    'algeqn : ID COLON mathterm EQUALS mathterm label end'
    if p[3][1] == 0:
        # this will probably be the most common case, so catch
        # it to avoid adding unnecessary terms
    	p[0] = ('algeqn', p[1], p[5], p[6])
    else:
        # subtract LHS from RHS to make a term that equals 0
        p[0] = ('algeqn', p[1], ('mathterm', ('arithmetic', '-', p[5], p[3])), p[6])

def p_diffeqn_noaux(p):
    'diffeqn : diffterm EQUALS mathterm label end'
    p[0] = ('diffeqn', p[1], p[3], p[4], ())

def p_diffeqn_aux(p):
    'diffeqn : diffterm auxterm EQUALS mathterm label end'
    p[0] = ('diffeqn', p[1], p[4], p[5], p[2])

def p_diffterm(p):
    'diffterm : ID PRIME'
    p[0] = p[1]

def p_auxterm_noquant(p):
    '''auxterm : PLUS ID PRIME
               | MINUS ID PRIME'''
    p[0] = ('auxterm', p[1], decimal.Decimal(1), p[2])

def p_auxterm_quant(p):
    '''auxterm : PLUS NUMBER ID PRIME
               | MINUS NUMBER ID PRIME'''
    p[0] = ('auxterm', p[1], p[2], p[3])

def p_auxterm_append_noquant(p):
    '''auxterm : auxterm PLUS ID PRIME
               | auxterm MINUS ID PRIME'''
    p[0] = p[1] + (p[2], decimal.Decimal(1), p[3])

def p_auxterm_append_quant(p):
    '''auxterm : auxterm PLUS NUMBER ID PRIME
               | auxterm MINUS NUMBER ID PRIME'''
    p[0] = p[1] + (p[2], p[3], p[4])

def p_rateterm_default(p):
    'rateterm : LBRACE arglist RBRACE'
    p[0] = ('rateterm', 'explicit', p[2])

def p_rateterm_special(p):
    'rateterm : LBRACE ID COLON arglist RBRACE'
    p[0] = ('rateterm', p[2], p[4])

def p_label(p):
    'label : LABEL'
    p[0] = ('label', p[1])

def p_nolabel(p):
    'label : empty'
    p[0] = ('label', '')

def p_bound(p):
    '''bound : ID LT mathterm label end
             | ID LE mathterm label end
             | ID GT mathterm label end
             | ID GE mathterm label end'''
    p[0] = ('bound', p[1], p[2], p[3], p[4])

def p_softbound(p):
    'softbound : TILDE bound'
    p[0] = ('softbound', p[2])

def p_constraint(p) :
    '''constraint : bound
                  | softbound'''
    p[0] = ('constraint', p[1])

def p_assign(p):
    'assign : ID EQUALS mathterm label end'
    p[0] = ('assign', p[1], p[3], p[4], False)

def p_init_assign(p):
    'assign : ID INIT mathterm label end'
    p[0] = ('assign', p[1], p[3], p[4], True)

def p_empty(p):
    'empty :'
    pass

def p_error(p):
    global compilationInfo
    compilationInfo['errors'].append(p)
    if None == p:
        print >> sys.stderr, 'Syntax error (unexpected EOF)'
        compilationInfo['messages'].append('Syntax error: unexpected EOF')
        compilationInfo['lines'].append('END')
        compilationInfo['files'].append(currentFile)
    else:
        print >> sys.stderr, 'Syntax error at token:', p
        compilationInfo['messages'].append("Syntax error at token '%s' [%s]" % (p.value, p.type))
        compilationInfo['lines'].append(p.lineno)
        compilationInfo['files'].append(currentFile)
        while 1:
            tok = yacc.token()
            if not tok or tok.type == 'END': break
        yacc.restart()

# module global variable for holding state information
# should probably try to migrate this into something more encapsulated
compilationInfo = {'errors':[], 'messages':[], 'files':[], 'lines':[]}
currentFile = None

def get_lexer_parser():    
    lexer = lex.lex(module=bcmd_lex)
    parser = yacc.yacc()
    return (lexer, parser)

# run this file directly to test parser
if __name__ == '__main__':
        try:
            filename = sys.argv[1]
            f = open(filename)
            data = f.read()
            f.close()
        except IndexError:
            sys.stdout.write("Reading from standard input:\n")
            data = sys.stdin.read()

	import pprint
	
	lexParse = get_lexer_parser()
        result = lexParse[1].parse(data, lexer=lexParse[0])
        
        nErr = len(compilationInfo['errors'])
        if nErr == 1:
            print >> sys.stderr, 'Compilation failed with 1 syntax error'
        elif nErr > 1:
            print >> sys.stderr, 'Compilation failed with %d syntax errors' % nErr
        pprint.pprint(result)

