# write documentation in LaTeX format
import sys
import os
import os.path
import re
import datetime, time
import decimal

# template details
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(THIS_DIR + '/templates')
HEADER = os.path.join(TEMPLATE_DIR, 'header.tex')
FOOTER = os.path.join(TEMPLATE_DIR, 'footer.tex')

def writeDoc(model, config):
    with open(os.path.join(config['outdir'], config['latex']), 'w') as f:
        printHeader(f, model, config)
        printOverview(f, model, config)
        printDiffs(f, model, config)
        printAlgs(f, model, config)
        printReactions(f, model, config)
        printRoots(f, model, config)
        printIntermeds(f, model, config)
        printParameters(f, model, config)
        printFooter(f, model, config)
        
def printHeader(file, model, config):   
    with open(HEADER) as src:
        for line in src:
            file.write(line.replace('__NAME__', config['name']))

def printFooter(file, model, config):
    with open(FOOTER) as src:
        for line in src:
            file.write(line)

def printOverview(file, model, config):
    print >> file, '\\section{Overview}\n'
    desc = '\n'.join([x for x in model['modeldocs'] if not (x.startswith('+') or x.startswith('@') or x.startswith('$') or x.startswith('~'))])
    print >> file, desc
    print >> file, ''
    print >> file, '\\begin{itemize}'
    print >> file, '\\item %d differential state variables' % len(model['diffs'])
    print >> file, '\\item %d algebraic state variables' % len(model['algs'])
    print >> file, '\\item %d intermediate variables' % len(model['intermeds'])
    print >> file, '\\item %d parameters' % len(model['params'])
    print >> file, '\\item %d declared inputs' % len(model['inputs'])
    print >> file, '\\item %d default outputs' % len(model['outputs'])
    print >> file, '\\end{itemize}\n'

def printReactions(file, model, config):
    if not model['reactions']:
        return
    
    print >> file, '\\section{Chemical Reactions}\n'
    
    for reac in sorted(model['reactions'].keys(), key=lambda s: s.lower()):
        # merge forward/reverse pairs into single two-way reactions
        if reac.endswith('_reverse') and (reac[:-7] + 'forward') in model['reactions']:
            continue
        
        op = '->'
        
        # collect terms and forward rate
        lhs = ''
        for term in model['reactions'][reac]['lhs']:
            stoich = translate(term['mathterm_unmod'], model, config)[0]           
            try:
                dec = decimal.Decimal(stoich)
                if dec == 1:
                    stoich = ''
            except:
                pass
            
            # we add spacing to stop the stoich and chem running together
            if stoich:
                stoich = stoich + ' \\; '
            
            chem = latexName(term['chem'], model)
            if lhs:
                lhs = '%s + %s %s' % (lhs, stoich, chem)
            else:
                lhs = '%s %s' % (stoich, chem)
            
        
        rhs = ''
        for term in model['reactions'][reac]['rhs']:
            stoich = translate(term['mathterm_unmod'], model, config)[0]
            try:
                dec = decimal.Decimal(stoich)
                if dec == 1:
                    stoich = ''
            except:
                pass
            
            if stoich:
                stoich = stoich + ' \\; '
            
            chem = latexName(term['chem'], model)
            if rhs:
                rhs = '%s + %s %s' % (rhs, stoich, chem)
            else:
                rhs = '%s %s' % (stoich, chem)
        
        fspec = model['reactions'][reac]['ratespec']
        if fspec[1] == 'MA':
            forward = 'MA'
        elif fspec[1] == 'MM':
            forward = 'MM'
        else:
            forward = '{%s}' % translate(fspec[2][1][1], model, config)[0]
        
        # if there's a reverse reaction, get that rate too
        if reac.endswith('_forward') and (reac[:-7] + 'reverse') in model['reactions']:
            rspec = model['reactions'][reac[:-7] + 'reverse']['ratespec']
            if rspec[1] == 'MA':
                reverse = 'MA'
            elif rspec[1] == 'MM':
                reverse = 'MM'
            else:
                reverse = '{%s}' % translate(fspec[2][1][1], model, config)[0]            
            op = '<->'
        else:
            reverse = ''
            rspec = ()
        
        print >> file, '\\begin{equation}'
        print >> file, '\\ce{%s %s[%s][%s] %s}' % (lhs, op, forward, reverse, rhs)
        print >> file, '\\end{equation}\n'
        
        if config.get('latex-display-style', True):
            display = ' \displaystyle '
        else:
            display = ''
        
        if forward == 'MA':
            if reverse:
                print >> file, 'Mass Action kinetics are assumed for the forward reaction, with calculated rate term'
            else:
                print >> file, 'Mass Action kinetics are assumed, with calculated rate term'
            print >> file, '$%s %s$.' % (display, translate(model['reactions'][reac]['rate']['mathterm'], model, config)[0])
        elif forward == 'MM':
            if reverse:
                print >> file, 'Michaelis-Menten kinetics are assumed for the forward reaction, with calculated rate term'
            else:
                print >> file, 'Michaelis-Menten kinetics are assumed, with calculated rate term'
            print >> file, '$%s %s$.' % (display, translate(model['reactions'][reac]['rate']['mathterm'], model, config)[0])
        
        if reverse == 'MA':
            print >> file, 'Mass Action kinetics are assumed for the reverse reaction, with calculated rate term'
            print >> file, '$%s %s$.' % (display, translate(model['reactions'][reac[:-7] + 'reverse']['rate']['mathterm'], model, config)[0])
        elif reverse == 'MM':
            print >> file, 'Michaelis-Menten kinetics are assumed for the reverse reaction, with calculated rate term'
            print >> file, '$%s %s$.' % (display, translate(model['reactions'][reac[:-7] + 'reverse']['rate']['mathterm'], model, config)[0])   
        
def latexName(name, model, insert=True):
    if 'latex' in model['symbols'][name]:
        return model['symbols'][name]['latex']
    
    stripped = name.strip('_')
    pieces = [x for x in stripped.split('_') if x]
    
    if not pieces:
        result = '\\mathbf{ERROR}'
    elif len(pieces) == 1:
        result = pieces[0]
    else:
        result = '%s_{%s}' % (pieces[0], ','.join(pieces[1:]))
    
    if insert:
        model['symbols'][name]['latex'] = result
    
    return result

def printDiffs(file, model, config):
    if not model['diffs']:
        return
    
    print >> file, '\\section{Differential Equations}\n'
    tt = latexName(model['symlist'][0], model)
    first = True
    
    if config.get('eq-align', True):
        print >> file, '\\begin{align}',
    
    for name in sorted(model['diffs'], key=lambda s: s.lower()):
        lhs = '\\frac{\\mathrm{d}%s}{\\mathrm{d}%s}' % (latexName(name, model), tt)
        for aux in model['auxiliaries'][name]:
            mass = aux[0]
            if mass < 0:
                mass = -mass
                op = '-'
            else:
                op = '+'
            if mass == 1:
                mstr = ''
            else:
                mstr = str(mass)
            lhs = lhs + op + mstr + '\\frac{\\mathrm{d}%s}{\\mathrm{d}%s}' % (latexName(aux[1], model), tt)
        
        rhs = substitute(model['symbols'][name]['diffs'][0], model, config)
        
        if config.get('eq-align', True):
            if first:
                first = False
                print >> file, ''
            else:
                print >> file, '\\\\'
            
            print >> file, '%s &= %s' % (lhs, rhs),
        else:
            print >> file, '\\begin{equation}'
            print >> file, '%s = %s' % (lhs, rhs)
            print >> file, '\\end{equation}\n'

    if config.get('eq-align', True):
        print >> file, '\n\\end{align}\n'

def printAlgs(file, model, config):
    if not model['algs']:
        return
    
    print >> file, '\\section{Algebraic Equations}\n'
    first = True
    
    if config.get('eq-align', True):
        print >> file, '\\begin{align}',
    
    for name in sorted(model['algs'], key=lambda s: s.lower()):
        lhs = substitute(model['symbols'][name]['algs'][0], model, config)
        
        if config.get('eq-align', True):
            if first:
                first = False
                print >> file, ''
            else:
                print >> file, '\\\\'
            
            print >> file, '%s &= 0' % lhs,
        else:
            print >> file, '\\begin{equation}'
            print >> file, '%s = 0' % lhs
            print >> file, '\\end{equation}\n'

    if config.get('eq-align', True):
        print >> file, '\n\\end{align}\n'


def printRoots(file, model, config):
    printVars(sorted(model['roots'], key=lambda s: s.lower()), 'State Variables', file, model, config, omit_expr=True)

def printIntermeds(file, model, config):
    printVars(sorted(model['intermeds'], key=lambda s: s.lower()), 'Intermediate Variables', file, model, config)

def printParameters(file, model, config):
    printVars(sorted(model['params'], key=lambda s: s.lower()), 'Parameters', file, model, config, omit_expr=True)

def printVars(vars, title, file, model, config, omit_expr=False):
    if vars:
        print >> file, '\\section{%s}\n' % title

        if config.get('latex-tabular', False):
            if omit_expr:
                print >> file, '\\begin{longtable}{l p{2.5cm} l p{5cm}}'
                print >> file, '\\hline'
                print >> file, 'Symbol & Units & Initialiser & Notes \\\\'            
            else:
                print >> file, '\\begin{longtable}{l p{2.5cm} l l p{5cm}}'
                print >> file, '\\hline'
                print >> file, 'Symbol & Units & Initialiser & Expression & Notes \\\\'
            print >> file, '\\hline'
        else:
            print >> file, '\\begin{description}'
            
        for name in vars:
            printVar(name, file, model, config, omit_expr)

        if config.get('latex-tabular', False):
            print >> file, '\\hline'
            print >> file, '\\end{longtable}\n'
        else:
            print >> file, '\\end{description}\n'

def printVar(name, file, model, config, omit_expr=False):
    sym = model['symbols'][name]
    
    docs = ''
    for line in sym['docs']:
        if line.startswith('+') or line.startswith('@') or line.startswith('$') or line.startswith('~'):
            pass
        elif line == '':
            if config.get('latex-tabular', False):
                docs = docs + ' '
            else:
                docs = docs + '\\\\\n'
        else:
            docs = docs + ' ' + line
    
    units = sym.get('units', 'not defined')

    inits = [x for x in sym['assigns'] if x['init']]
    noninits = [x for x in sym['assigns'] if not x['init']]
    
    if inits:
        init = substitute(inits[0], model, config)
    else:
        init = '0'
    
    if noninits:
        noninit = substitute(noninits[0], model, config)
        if not config.get('latex-tabular', False):
            noninit = '= %s' % noninit
    else:
        noninit = ''
    
    if config.get('latex-display-style', True):
        display = ' \displaystyle '
    else:
        display = ''
    
    if config.get('latex-tabular', False):
        tsym = '$%s%s$' % (display, latexName(name, model))
        tinit = '$%s%s$' % (display, init)
        if omit_expr:
            print >> file, '%s & %s & %s & %s \\\\' % (tsym, units, tinit, docs)        
        else:
            texpr = '$%s%s$' % (display, noninit)
            print >> file, '%s & %s & %s & %s & %s \\\\' % (tsym, units, tinit, texpr, docs)
    else:
        print >> file, '\\item[$%s$] $%s %s \\;$\\\\' % (latexName(name, model), display, noninit)
        if config.get('latex-include-code', True):
            print >> file, 'Implementation Name: \\texttt{%s}\\\\' % name.replace('_', '\\_')
        print >> file, 'Units: %s\\\\' % units
        print >> file, 'Initial value: $%s %s$\\\\' % (display, init)
        print >> file, '%s' % docs


def substitute(init, model, config):
    # init is an assigns entry, ie a dict with expr, depends, etc
    # we don't yet construct mathterms for diff eqs from chem eqs, so have to check
    if 'mathterm' in init:
        expr = translate(init['mathterm'], model, config)[0]
    else:
        expr = init['expr']

        # need to have some way of managing collisions here -- this will eventually get more sensible
        # but for now, we substitute long ids before short
        for dep in sorted(init['depends'], key=lambda x:-len(x)):
            expr = expr.replace(dep, latexName(dep, model))
    
    return expr

def translate(math, model, config):
    if isinstance(math, decimal.Decimal):
        # yet another formatting special case, purely because these annoy me!
        result = str(math)
        if result.endswith('.0'):
            result = result[:-2]
        return (result, '')
    if isinstance(math, str):
        return (latexName(math, model), '')
    if math[0] == 'function':
        if len(math) < 3:
            args = ''
        else:
            args = ', '.join([ translate(x[1], model, config)[0] for x in math[2][1:] ])
        return ('\\mathrm{%s}\\left( %s \\right)' % (math[1], args), '')
    if math[0] == 'conditional':
        return ('%s \; \mathbf{?} \;  %s \; \mathbf{:} \; %s' % (translate_binop(math[1], model, config)[0],
                                                                 translate(math[2][1], model, config)[0],
                                                                 translate(math[3][1], model, config)[0] ), '')
    if math[0] == 'arithmetic':
        return translate_binop(math, model, config)
    
    return ('[ERROR]', '')

def translate_binop(math, model, config):
    lhs, lop = translate(math[2][1], model, config)
    rhs, rop = translate(math[3][1], model, config)
    
    # check for pure numbers, because we want to handle some special cases
    try:
        L = decimal.Decimal(lhs)
    except:
        L = None
    
    try:
        R = decimal.Decimal(rhs)
    except:
        R = None    
    
    # dodgy special case, whereby ops between two numeric constants
    # are executed explicitly inline here (arguably this should be done in the compiler, but...)
    if config.get('latex-calc', True) and L is not None and R is not None:
        if math[1] == '*':
            result = str(L*R)
        elif math[1] == '+':
            result = str(L+R)
        elif math[1] == '/':
            result = str(L/R)
        elif math[1] == '-':
            result = str(L-R)
        elif math[1] == '^':
            result = str(L**R)
        else:
            # TODO: handle comparison ops here
            return ('[ERROR]', '')
            
        # formatting special case, as above
        if result.endswith('.0'):
            result = result[:-2]
        return (result, '')
        
    if math[1] == '*':
        if lop == '+' or lop == '-':
            lhs = ' \\left( %s \\right) ' % lhs
        if rop == '+' or rop == '-':
            rhs = ' \\left( %s \\right) ' % rhs

        # special cases: numbers get a times symbol rather than just being      
        if L is not None:
            # nested special case for our stupid handling of unary minus in the parser...
            if L == -1:
                op = ''
                lhs = ''
                rhs = '-%s' % rhs
            # and to eliminate superfluous multiplications by 1
            elif L == 1:
                op = ''
                lhs = ''
            else:
                # maybe make this an option later, but for
                # now let's try not using times for numbers on the left
                op = ''
        elif R is not None:
            if R == 1:
                op = ''
                rhs = ''
            else:
                op = '\\times'
        else:
            op = '\\,'
        return (' %s %s %s ' % (lhs, op, rhs), '*')
    
    if math[1] == '/':
        return (' \\frac{%s}{%s} ' % (lhs, rhs), '/')
    
    if math[1] == '^':
        if lop != '':
            lhs = ' \\left( %s \\right) ' % lhs
        return (' %s^{%s} ' % (lhs, rhs), '^')
        
    if math[1] == '+':
        # another dodgy special case: convert + - into -
        if rhs.strip().startswith('-'):
            return( ' %s - %s ' % (lhs, rhs.strip()[1:]), '-' )
        # and yet another, perhaps dodgiest of all: convert -a + b into b - a
        if lhs.strip().startswith('-'):
            return( ' %s - %s ' % (rhs, lhs.strip()[1:]), '-' )
        return (' %s + %s ' % (lhs, rhs), '+')
        
    if math[1] == '-':
        if rop == '-':
            rhs = ' \\left( %s \\right) ' % rhs
        return (' %s - %s ' % (lhs, rhs), '-')
    
    # all remaining binops are logical
    # these only occur in conditions and have the weakest precedence, so we never bracket
    return (' %s %s %s ' %(lhs, math[1], rhs), '')
