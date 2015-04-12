# export model to half-baked SBML (there is no other kind)
# although this is not really a documentation format,
# the process is similar enough structurally to group with those modules
import sys
import os
import os.path
import re
import datetime, time
import decimal

try:
    import libsbml as sb
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

LEVEL = 3
VERSION = 1

DEFCOMP = 'Here'

# definitions of a few common functions in MathML form
# this is odious, but that's SBML for you
MIN_XML = """<math xmlns="http://www.w3.org/1998/Math/MathML">
      <lambda>
        <bvar>
          <ci> x </ci>
        </bvar>
        <bvar>
          <ci> y </ci>
        </bvar>
        <piecewise>
          <piece>
            <ci> x </ci>
            <apply>
              <lt/>
              <ci> x </ci>
              <ci> y </ci>
            </apply>
          </piece>
          <otherwise>
            <ci> y </ci>
          </otherwise>
        </piecewise>
      </lambda>
    </math>
"""

MAX_XML = """<math xmlns="http://www.w3.org/1998/Math/MathML">
      <lambda>
        <bvar>
          <ci> x </ci>
        </bvar>
        <bvar>
          <ci> y </ci>
        </bvar>
        <piecewise>
          <piece>
            <ci> x </ci>
            <apply>
              <gt/>
              <ci> x </ci>
              <ci> y </ci>
            </apply>
          </piece>
          <otherwise>
            <ci> y </ci>
          </otherwise>
        </piecewise>
      </lambda>
    </math>
"""

HEAVI_XML = """<math xmlns="http://www.w3.org/1998/Math/MathML">
      <lambda>
        <bvar>
          <ci> x </ci>
        </bvar>
        <bvar>
          <ci> y </ci>
        </bvar>
        <piecewise>
          <piece>
            <cn> 1 </cn>
            <apply>
              <leq/>
              <ci> x </ci>
              <ci> y </ci>
            </apply>
          </piece>
          <otherwise>
            <cn> 0 </cn>
          </otherwise>
        </piecewise>
      </lambda>
    </math>
"""

# map a few unknown function names to the above definitions
UNKNOWNS = { 'fmin': MIN_XML, 'min': MIN_XML,
             'fmax': MAX_XML, 'max': MAX_XML,
             'heavi': HEAVI_XML }

class SBMLExportException(Exception):
    '''Exception for unsupported model features.'''

def writeDoc(model, config):
    # create the container
    doc = sb.SBMLDocument(LEVEL, VERSION)

    # we define no units at all
    sbml = doc.createModel()
    sbml.setId(config['name'])
    
    # insert model content
    # -- for the moment many of these things will do nothing...
    defineFunctions(sbml, model, config)
    defineUnits(sbml, model, config)
    defineCompartments(sbml, model, config)
    defineSpecies(sbml, model, config)
    defineParameters(sbml, model, config)
    defineInitialisers(sbml, model, config)
    defineRules(sbml, model, config)
    defineConstraints(sbml, model, config)
    defineReactions(sbml, model, config)
    defineEvents(sbml, model, config)
    
    sb.writeSBMLToFile(doc, os.path.join(config['outdir'], config['sbml']))


def defineFunctions(sbml, model, config):
    # scant effort to support a tiny number of functions
    # that are not already known to SBML
    # may expand at some point, but don't bet on it
    for unknown in model['unknown']:
        fn = sbml.createFunctionDefinition()
        fn.setId(unknown)
        if unknown in UNKNOWNS:
            fn.setMath(sb.readMathMLFromString(UNKNOWNS[unknown]))

# for the time being we define no units at all, which is consistent
# with BCMD's own approach -- we could possibly add details from doc comments
# but life's too short
def defineUnits(sbml, model, config):
    # TODO
    pass

# it seems like some explicit compartment must be declared, so...
def defineCompartments(sbml, model, config):
    space = sbml.createCompartment()
    space.setId(DEFCOMP)
    space.setSize(1)
    space.setConstant(True)

# starting strategy is that root variables are declared as species
# and all other symbols as parameters
# -- zarquon only knows whether that makes any sense...
def defineSpecies(sbml, model, config):
    for root in model['roots']:
        spec = sbml.createSpecies()
        spec.setId(root)
        spec.setConstant(False)
        spec.setCompartment(DEFCOMP)
        spec.setHasOnlySubstanceUnits(True)
        spec.setBoundaryCondition(False)

def defineParameters(sbml, model, config):
    for name in model['symbols']:
        if name not in model['roots']:
            pram = sbml.createParameter()
            pram.setId(name)
            pram.setConstant(False)

def defineInitialisers(sbml, model, config):
    for name in model['symbols']:
        sym = model['symbols'][name]

        # we are not allowed to define both an InitialAssignment and an AssignmentRule
        # for any symbol, so any non-trivial initialisers in this context just get ignored
        noninits = [x for x in sym['assigns'] if not x['init']]
    
        inits = [x for x in sym['assigns'] if x['init']]
        
        if inits and not noninits:
            rule = sbml.createInitialAssignment()
            rule.setSymbol(name)
            rule.setMath(convert(inits[0], model, config))
        else:
            # default initialisation gets set on the element itself, rather
            # than specifying a rule
            elem = sbml.getElementBySId(name)
            if name in model['roots']:
                elem.setInitialAmount(0)
            else:
                elem.setValue(0)

def defineRules(sbml, model, config):
    for name in model['symbols']:
        sym = model['symbols'][name]
        if name in model['diffs']:
            # SBML doesn't seem to support auxiliary terms, so bail if we encounter such
            if name in model['auxiliaries']:
                if model['auxiliaries'][name]:
                    raise SBMLExportException('SBML does not allow auxiliary terms in differential equations')
            # note that the following includes diff eqs derived from chemical reactions
            # the reactions themselves are just too tiresome to translate!
            rule = sbml.createRateRule()
            rule.setVariable(name)
            rule.setMath(convert(sym['diffs'][0], model, config))                
        elif name in model['algs']:
            if sym['algs']:
                rule = sbml.createAlgebraicRule()
                rule.setMath(convert(sym['algs'][0], model, config))
        else:
            noninits = [x for x in sym['assigns'] if not x['init']]
            if noninits:
                rule = sbml.createAssignmentRule()
                rule.setVariable(name)
                rule.setMath(convert(noninits[0], model, config))
        

# SBML constraints correspond roughly to BCMD's unimplemented 'soft' constraints
# since we don't support those ourselves yet, there is nothing to do here
def defineConstraints(sbml, model, config):
    # TODO (but preferably not)
    pass

# the way SBML handles reactions is sufficiently annoyingly different from the
# way BCMD does that we're just going to omit the bloody things entirely and
# use our calculated differential equations directly. life is too damn short!
def defineReactions(sbml, model, config):
    # TODO (but preferably not)
    pass

def defineEvents(sbml, model, config):
    # TODO
    pass


## TEMPORARY, for info
## TODO: kill this
def printVar(name, file, model, config, omit_expr=False):
    sym = model['symbols'][name]
    
    for line in sym['docs']:
        if line.startswith('+') or line.startswith('@') or line.startswith('$') or line.startswith('~'):
            pass
        else:
            print >> file, '## %s' % line
    
    units = sym.get('units', '')
    if units:
        print >> file, '## ~ %s' % units
    
    latex = sym.get('latex', '')
    if latex:
        print >> file, '## $%s$' % latex
    
    tags = ' '.join(sym.get('tags', []))
    if tags:
        print >> file, '## + %s' % tags

    if not omit_expr:
        noninits = [x for x in sym['assigns'] if not x['init']]
        if noninits:
            noninit = substitute(noninits[0], model, config)
            print >> file, '%s = %s' % (name, noninit)

    inits = [x for x in sym['assigns'] if x['init']]
    if inits:
        init = substitute(inits[0], model, config)
    else:
        init = '0'
    print >> file, '%s := %s' % (name, init)
    
    for constraint in sym['constraints']:
        # at present the compiler doesn't store a mathexpr for constraints, so use the old expr stuff
        # (this will also need to be extended if and when soft constraints ever get implemented)
        invtest = { '>':'<=', '>=':'<', '<':'>=', '<=':'>'}.get(constraint['test'], 'ERROR')
        if not (name in model['chemicals'] and (invtest == '>=') and constraint['expr']=='0'):
            print >> file, '%s %s %s' % ( name, invtest, constraint['expr'] )
    
    print >> file, ''

# construct an ASTNode for an expression -- for the moment this
# just does a quick formula parse on the expr form
# TODO: properly translate the mathexpr, if available
def convert(expr, model, config):
    # this will fail on unsupported syntax, notably the conditional operator ?:
    return sb.parseL3Formula(expr['expr'])
    
#   # init is an assigns entry, ie a dict with expr, depends, etc
#   # we don't yet construct mathterms for diff eqs from chem eqs, so have to check
#     if 'mathterm' in init:
#         expr = translate(init['mathterm'], model, config)[0]
#     else:
#         expr = init['expr']
# 
#         # need to have some way of managing collisions here -- this will eventually get more sensible
#         # but for now, we substitute long ids before short
#         for dep in sorted(init['depends'], key=lambda x:-len(x)):
#             expr = expr.replace(dep, latexName(dep, model))
# 
#     return expr

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
        return ('%s(%s)' % (math[1], args), '')
    if math[0] == 'conditional':
        return ('%s ? %s : %s' % (translate_binop(math[1], model, config)[0],
                                  translate(math[2][1], model, config)[0],
                                  translate(math[3][1], model, config)[0]), '')
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
        
    if math[1] == '*':
        if lop == '+' or lop == '-':
            lhs = '(%s)' % lhs
        if rop == '+' or rop == '-':
            rhs = '(%s)' % rhs

        # numeric special cases     
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
                op = '*'
        elif R is not None:
            if R == 1:
                op = ''
                rhs = ''
            else:
                op = '*'
        else:
            op = '*'
        return (('%s %s %s' % (lhs, op, rhs)).strip(), '*')
    
    if math[1] == '/':
        if lop == '+' or lop == '-':
            lhs = '(%s)' % lhs
        if rop == '+' or rop == '-' or rop == '*' or rop == '/':
            rhs = '(%s)' % rhs
        return ('%s / %s' % (lhs, rhs), '/')
    
    if math[1] == '^':
        if lop != '':
            lhs = '(%s)' % lhs
        return ('%s^(%s)' % (lhs, rhs), '^')
        
    if math[1] == '+':
        # another dodgy special case: convert + - into -
        if rhs.strip().startswith('-'):
            return( '%s - %s' % (lhs, rhs.strip()[1:]), '-' )
        # and yet another, perhaps dodgiest of all: convert -a + b into b - a
        if lhs.strip().startswith('-'):
            return( '%s - %s' % (rhs, lhs.strip()[1:]), '-' )
        return ('%s + %s' % (lhs, rhs), '+')
        
    if math[1] == '-':
        if rop == '-':
            rhs = '(%s)' % rhs
        return ('%s - %s' % (lhs, rhs), '-')
    
    # all remaining binops are logical
    # these only occur in conditions and have the weakest precedence, so we never bracket
    return ('%s %s %s' %(lhs, math[1], rhs), '')
