import sys
import os
import decimal
import string
import logger

# template configuration: in theory this stuff could be
# modified at runtime, though in practice that seems unlikely
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(THIS_DIR + '/templates')
TEMPLATES = [ '01_header.c_template', '02_errors.c_template', '03_prototypes.c_template', '05_functions.c_template' ]

# generate the C code from a parsed model
# much of the code is unchanging boilerplate, and much of that
# is simply copied direct from several template files
# where the code is dependent on the model it is constructed
# in a bunch of subsidiary functions below -- at present
# these are a rather ugly mix of literal C strings and
# variable substitutions -- maybe look into making this
# less horrible in future?
def generateSource(model, config, template_dir=TEMPLATE_DIR):
    f = open(template_dir + '/' + TEMPLATES[0])
    src = f.read()
    f.close()
    f = open(template_dir + '/' + TEMPLATES[1])
    src = src + f.read()
    f.close()
    
    src = src + generateModelVars(model, config)
    
    f = open(template_dir + '/' + TEMPLATES[2])
    src = src + f.read()
    f.close()
    
    src = src + generateEmbeds(model)
    src = src + generateModelFuncs(model, config)
    
    f = open(template_dir + '/' + TEMPLATES[3])
    src = src + f.read()
    f.close()
    
    return src

# generate the model variables segment
def generateModelVars(model, config):
    diffcount = len(model['diffs'])
    algcount = len(model['algs'])
    symcount = len(model['symlist'])
    varcount = diffcount + algcount
    src = '/* Model-specific constants and statics */\n'
    src = src + 'const char* MODEL_NAME = "' + config['name'] + '";\n'
    
    if model['version']:
        src = src + 'const char* MODEL_VERSION = "' + model['version'] + '";\n'
    else:
        src = src + 'const char* MODEL_VERSION = "(version not specified)";\n'
    
    if model['diagonal']:
        src = src + 'const int DIAGONAL = 1;\n'
        src = src + 'const int REQUIRE_MASS = 0;\n'
    else:
        src = src + 'const int DIAGONAL = 0;\n'
        src = src + 'const int REQUIRE_MASS = 1;\n'
    
    src = src + 'const unsigned int DIFF_EQ_COUNT = ' + str(diffcount) + ';\n'
    src = src + 'const unsigned int ALGEBRAIC_COUNT = ' + str(algcount) + ';\n'
    src = src + 'const unsigned int VAR_COUNT = ' + str(diffcount + algcount) + ';\n'
    src = src + 'const unsigned int SYMBOL_COUNT = ' + str(symcount) + ';\n\n'
    
    src = src + 'static char* SYMBOLS[' + str(symcount) + '] = \n{\n'
    src = src + formatArray(model['symlist'])
    src = src + '};\n\n'
    
    src = src + 'static char* ROOTS[' + str(varcount) + '] = \n{\n'
    src = src + formatArray(model['diffs'] + model['algs'])
    src = src + '};\n\n'
    
    if model['intermeds']:
        src = src + 'static double INTERMEDIATES[' + str(len(model['intermeds'])) + '] = {0};\n\n'
    
    indices = [0]
    for name in model['outputs']:
        indices.append(model['symbols'][name]['index'])
    
    src = src + 'static int DEFAULT_FIELDS[' + str(len(indices)) + '] = \n{\n'
    src = src + formatArray(indices, width=10, quote='')
    src = src + '};\n'
    src = src + 'static OutputSpec DEFAULT_OUTSPEC = { ' + str(len(indices)) + ', DEFAULT_FIELDS };\n\n'
    
    return src

# generate segment for embedded C chunks
# (by just pasting them all together -- this stuff is not checked)
def generateEmbeds(model):
    return '/* Embedded C code from the model, if any */\n\n' + '\n'.join(model['embeds']) + '\n\n'
    
# generate the model functions segment
def generateModelFuncs(model, config):
    if config['unused']:
        targets = model['assigned']
    else:
        targets = list(model['assigned'] - model['unused'])
    
    src = '/* Model-specific functions */\n'
    src = src + generateModelInit(model, config, targets)
    src = src + generateParamUpdate(model, config, targets)
    src = src + generateSaveY(model, config)
    src = src + generateSaveIntermediates(model, config)
    src = src + generateCarryForward(model, config)
    src = src + generateRHS(model, config, targets)
    src = src + generateConstraints(model, config)
    return src

# generate the model initialisation code
def generateModelInit(model, config,  targets):
    src = '''
/* Initialise parameters with any values known at compile time.
   (NB: these may be overwritten by runtime values) */
void model_init()
{
'''
    if not model['diagonal']:
        src = src + '    double* mass = radau5_getMassMatrix();\n\n'
    
    if config['debug']: src = src + '    fprintf(stderr, "# Initialising parameters\\n");\n\n'
    
    independent = model['assignments']['independent']
    for ii in range(len(independent['names'])):
        name = independent['names'][ii]
        if name in targets:
            expr = independent['exprs'][ii]
            idx = model['symbols'][name]['index']
            src = src + '    RPAR[' + str(idx) + '] = ' + str_i_expr(expr['i_expr'], model) + ';'
            src = src + '\t\t/* ' + name + '=' + expr['expr'] + ' */\n'
            if config['debug']:
                src = src + '    fprintf(stderr, "' + name + ' = %.17g\\n", RPAR[' + str(idx) + ']);\n'
    
    dependent = model['assignments']['dependent']
    for ii in range(len(dependent['names'])):
        name = dependent['names'][ii]
        if name in targets:
            expr = dependent['exprs'][ii]
            idx = model['symbols'][name]['index']
            src = src + '    RPAR[' + str(idx) + '] = ' + str_i_expr(expr['i_expr'], model) + ';'
            src = src + '\t\t/* ' + name + '=' + expr['expr'] + ' */\n'
            if config['debug']:
                src = src + '    fprintf(stderr, "' + name + ' = %.17g\\n", RPAR[' + str(idx) + ']);\n'
    
    src = src + '\n    constrain_params();\n'
    src = src + '\n    carry_forward();\n'

    if not model['diagonal']:
        idy = 0
        for item in model['diffs']:
            for aux in model['auxiliaries'][item]:
                auxname = aux[1]
                if auxname not in model['diffs']:
                    logger.error('Error: auxiliary term not in diffs: ' + auxname)
                else:
                    idx = model['diffs'].index(aux[1])
                    src = src + '\n    /* auxiliary diff eqn term: ' + item + "' : "
                    src = src + str(aux[0]) + " " + auxname + "' */\n"
                    
                    # idy indexes the equation, idx the crossref
                    # Fortran uses column-major order for matrices,
                    # which I *think* makes this the right way to index
                    src = src + '    mass[VAR_COUNT * ' + str(idx) + ' + ' + str(idy) + '] = ' + str(aux[0]) + ';\n'
            idy = idy + 1
    
    src = src + '}\n'
    return src

# generate param_update function
def generateParamUpdate(model, config, targets):
    src = '''
/* Propagate parameter changes to any dependent parameters */
void param_update()
{
'''
    step = model['assignments']['step']
    if len(step) > 0:
        if config['debug']: src = src + '    fprintf(stderr, "# Updating dependent parameters:\\n");\n\n'
        for ii in range(len(step['names'])):
            name = step['names'][ii]
            if name not in targets: continue
            expr = step['exprs'][ii]
            idx = model['symbols'][name]['index']
            
            src = src + '    RPAR[' + str(idx) + '] = ' + str_i_expr(expr['i_expr'], model, 'step') + ';'
            src = src + '\t\t/* ' + name + '=' + expr['expr'] + ' */\n'
            
            if config['debug']: src = src + '    fprintf(stderr, "' + name + ' = %.17g\\n", RPAR[' + str(idx) + ']);\n\n'
        
    else:
        src = src + '    /* no parameters to update for this model */\n'
    src = src + '}\n'
    return src


def generateSaveY(model, config):
    src = '''
/* Copy Y values into corresponding spaces in the RPAR array */
void save_y(double* y)
{
'''
    if config['debug']: src = src + '    fprintf(stderr, "# Saving Y estimates\\n");\n'    

    idy = 0
    for item in model['diffs'] + model['algs']:
        src = src + '    /* ' + item + ' */\n'
        src = src + '    RPAR[' + str(model['symbols'][item]['index']) + '] = y[' + str(idy) + '];\n'
        if config['debug']:
            src = src + '    fprintf(stderr, "' + item + ' = %.17g\\n", y[' + str(idy) + ']);\n'
        idy = idy + 1

    src = src + '}\n'
    return src

def generateSaveIntermediates(model, config):
    src = '''
/* Copy intermediate variables into corresponding spaces in the RPAR array */
void save_intermediates()
{
'''
    if config['debug']: src = src + '    fprintf(stderr, "# Saving intermediates\\n");\n'    

    idy = 0
    for item in model['intermeds']:
        src = src + '    /* ' + item + ' */\n'
        src = src + '    RPAR[' + str(model['symbols'][item]['index']) + '] = INTERMEDIATES[' + str(idy) + '];\n'
        if config['debug']:
            src = src + '    fprintf(stderr, "' + item + ' = %.17g\\n", INTERMEDIATES[' + str(idy) + ']);\n'
        idy = idy + 1

    src = src + '}\n'
    return src

def generateCarryForward(model, config):
    src = '''
/* Update Y array with corresponding values from the RPAR array */
void carry_forward()
{
'''
    if config['debug']: src = src + '    fprintf(stderr, "# Setting Y variables\\n");\n'    

    idy = 0
    for item in model['diffs'] + model['algs']:
        src = src + '    /* ' + item + ' */\n'
        src = src + '    Y[' + str(idy) + '] = RPAR[' + str(model['symbols'][item]['index']) + '];\n'
        if config['debug']:
            src = src + '    fprintf(stderr, "' + item + ' = %.17g\\n", Y[' + str(idy) + ']);\n'
        idy = idy + 1

    src = src + '}\n'
    return src


# generate right hand side function
def generateRHS(model, config, targets):
    src = '''
/* right hand side of main equation system */
void rhs(int* n, double* x, double* y, double* f, double* rpar, int* ipar)
{
    /* independent variable is always stored in RPAR[0] */
    RPAR[0] = *x;
    
    constrain_y(y);
    constrain_params();
        
'''
    if config['debug']: src = src + '    fprintf(stderr, "*** RHS step at %s = %.17g\\n", SYMBOLS[0], *x);\n'

    runtime = model['assignments']['runtime']
    if len(runtime['names']) > 0:
        lhs = model['diffs'] + model['algs']
        src = src + '\n    /* calculate dependent parameters and intermediate variables */\n'
        if config['debug']: src = src + '    fprintf(stderr, "# Calculating intermediates:\\n");\n\n'
        for ii in range(len(runtime['names'])):
            name = runtime['names'][ii]
            if name in lhs: continue
            if name not in targets: continue
            expr = runtime['exprs'][ii]
            idx = model['intermeds'].index(name)
            
            src = src + '    INTERMEDIATES[' + str(idx) + '] = ' + str_i_expr(expr['i_expr'], model, 'solve') + ';'
            src = src + '\t\t/* ' + name + '=' + expr['expr'] + ' */\n'
            
            if config['debug']: src = src + '    fprintf(stderr, "' + name + ' = %.17g\\n", INTERMEDIATES[' + str(idx) + ']);\n\n'

        src = src + '''
    constrain_intermediates();
    if ( SAVE_INTERMEDIATES )
        save_intermediates();
    
    constrain_params();
    
'''
    
    else:
        src = src + '\n    /* no dependent parameters or intermediates required for this model */\n'
    
    
    src = src + '\n    if ( f )'
    src = src + '\n    {'
    src = src + '\n        /* calculate output variables */\n'

    if config['debug']: src = src + '        fprintf(stderr, "# Calculating outputs:\\n");\n\n'
    
    idy = 0
    for name in model['diffs']:
        # for the moment we'll just assume that the right expression is always
        # the first in the list, and not even bother to look further
        expr = model['symbols'][name]['diffs'][0]
        src = src + '        /* ' + name + "' = " + expr['expr'] + ' */\n'
        src = src + '        f[' + str(idy) + '] = ' + str_i_expr(expr['i_expr'], model, 'solve') + ';\n'
        
        if config['debug']: src = src + '        fprintf(stderr, "' + name + '\' = %.17g\\n", f[' + str(idy) + ']);\n\n'

        idy = idy + 1
    
    for name in model['algs']:
        expr = model['symbols'][name]['algs'][0]
        src = src + '        /* ' + name + " = " + expr['expr'] + ' */\n'
        src = src + '        f[' + str(idy) + '] = ' + str_i_expr(expr['i_expr'], model, 'solve') + ';\n'
        
        if config['debug']: src = src + '        fprintf(stderr, "' + name + ' = %.17g\\n", f[' + str(idy) + ']);\n\n'

        idy = idy + 1
    
    src = src + '    }\n'
    src = src + '}\n'
    return src

def generateConstraints(model, config):
    src = '''
/* Enforce constraints on parameters/intermediates (if any). */
void constrain_params ()
{
'''
    targets = model['symbols'].keys()
    if not config['unused']:
        targets = list(set(targets) - model['unused'])
    
    for name in targets:
        sym = model['symbols'][name]
        for constraint in sym['constraints']:
            src = src + '    if ( RPAR[' + str(sym['index']) + '] ' + constraint['test'] + \
                  ' ' + str_i_expr(constraint['i_expr'], model) + ' )\n    {\n'
            
            if constraint['kind'] == 'bound':
                src = src + '        /* hard bound on ' + name + ' */\n'
                src = src + '        RPAR[' + str(sym['index']) + '] = ' + \
                      str_i_expr(constraint['i_expr'], model) + ';\n'
            else:
                src = src + '        /* TODO: handle soft bound on ' + name + ' */\n'
            src = src + '    }\n'

    src = src + '''}

void constrain_intermediates()
{
'''
    targets = model['intermeds']
    if not config['unused']:
        targets = list(set(targets) - model['unused'])
    
    for name in targets:
        idx = model['intermeds'].index(name)
        sym = model['symbols'][name]
        for constraint in sym['constraints']:
            src = src + '    if ( INTERMEDIATES[' + str(idx) + '] ' + constraint['test'] + \
                  ' ' + str_i_expr(constraint['i_expr'], model, 'solve') + ' )\n    {\n'
            
            if constraint['kind'] == 'bound':
                src = src + '        /* hard bound on ' + name + ' */\n'
                src = src + '        INTERMEDIATES[' + str(idx) + '] = ' + \
                      str_i_expr(constraint['i_expr'], model, 'solve') + ';\n'
            else:
                src = src + '        /* TODO: handle soft bound on ' + name + ' */\n'
            src = src + '    }\n'

    src = src + '''}

void constrain_y( double* y )
{
'''
    targets = model['diffs'] + model['algs']
    
    for name in targets:
        idx = targets.index(name)
        sym = model['symbols'][name]
        for constraint in sym['constraints']:
            src = src + '    if ( y[' + str(idx) + '] ' + constraint['test'] + \
                  ' ' + str_i_expr(constraint['i_expr'], model, 'solve') + ' )\n    {\n'
            
            if constraint['kind'] == 'bound':
                src = src + '        /* hard bound on ' + name + ' */\n'
                src = src + '        y[' + str(idx) + '] = ' + \
                      str_i_expr(constraint['i_expr'], model, 'solve') + ';\n'
            else:
                src = src + '        /* TODO: handle soft bound on ' + name + ' */\n'
            src = src + '    }\n'

    src = src + '''}

'''

    return src


# convert an i_expr tuple into C code with the appropriate
# data context
# recognised contexts are as follows:
#   'init' - model initialisation
#   'step' - after parameters have been assigned externally
#   'solve' - inside the solver RHS call
def str_i_expr(i_expr, model, context='init'):
    expr = ''
    for item in i_expr:
        if item[0] == 'literal':
            expr = expr + item[1]
        elif item[0] == 'symbol':
            expr = expr + str_i_symbol(item[1], model, context)
        else:
            # add a dummy symbol to produce a C compiler error
            logger.error('unknown item |%s| in i_expr' % str(item))
            expr = expr + 'ERROR_IN_IEXPR'
    
    return expr

# map a symbol appropriately for the given context
# (see above for supported contexts)
def str_i_symbol(name, model, context):
    if name in model['params']:
        # these are always used from RPAR
        return 'RPAR[' + str(model['symbols'][name]['index']) + ']'
    elif name in model['roots']:
        if context == 'solve':
            return 'y[' + str((model['diffs'] + model['algs']).index(name)) + ']'
        elif context == 'step':
            return 'Y[' + str((model['diffs'] + model['algs']).index(name)) + ']'
        else:
            return 'RPAR[' + str(model['symbols'][name]['index']) + ']'
    elif name in model['intermeds']:
        # temp array used during a solve, but not outside
        if context == 'solve':
            return 'INTERMEDIATES[' + str(model['intermeds'].index(name)) + ']'
        else:
            return 'RPAR[' + str(model['symbols'][name]['index']) + ']'
    
    else:
        logger.error('unknown symbol |%s| in i_expr' % name)
        return 'ERROR_IN_IEXPR'


## ------ utility functions ---------------

# generate a string containing the items of an array, formatted
# for embedding in code -- default settings are for string items,
# for numbers set quote=''
def formatArray(items, width=5, quote='"', inset='    ', sep=', ', end='\n'):
    src = ''
    idx = 0
    
    while idx + width < len(items):
        src = src + inset
        for jj in range(width):
            src = src + quote + str(items[idx + jj]) + quote + sep
        idx = idx + width
        src = src + end
    
    src = src + inset
    while idx + 1 < len(items):
        src = src + quote + str(items[idx]) + quote + sep
        idx = idx + 1
    
    src = src + quote + str(items[idx]) + quote + end
    
    return src
