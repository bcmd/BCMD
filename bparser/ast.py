# functions for processing the parsed syntax tree
import sys
import decimal
import string
import logger

# list of standard functions (from <math.h>) that are
# already known to be included in the destination
# NB: this list is fairly minimal -- the actual math.h
# for a contemporary C compiler is likely to include
# many more functions, but since we only use this for
# reporting purposes this list will do for now
# (these may eventually move to some other module)
STD_FUNCS = set(['acos', 'asin', 'atan', 'atan2', 'cos',
                 'cosh', 'sin', 'sinh', 'tan', 'tanh',
                 'exp', 'frexp', 'ldexp', 'log', 'log10',
                 'modf', 'pow', 'sqrt', 'ceil', 'fabs',
                 'floor', 'fmod'])

# shared non-negativity constraint for use with chemicals
NON_NEGATIVE = {'expr' : '0', 'i_expr' : (('literal', '0'),), 'kind' : 'bound', 'test' : '<'}

# when we need labels and they aren't supplied, use a simple
# integer counter to distinguish them
n_unlabelled = 0
def default_label(basename='unlabelled__'):
    global n_unlabelled
    n_unlabelled = n_unlabelled + 1
    return basename + str(n_unlabelled)

# process all the top level items in a parsed model AST
# working out what's in them and what their dependencies are
def process(merged, sources, independent='t'):
    work = {
                'roots' : [],
                'assigned' : set(),
                'chemicals' : {},
                'reactions' : {},
                'symbols' : {},
                'conflicts' : [],
                'functions' : set(),
                'embeds' : [],
                'required' : set(),
                'unused' : set(),
                'symlist' : [],
                'diffs' : [],
                'algs' : [],
                'auxiliaries' : {},
                'diagonal' : True,
                'version' : '',
                'params' : [],
                'intermeds' : [],
                'outputs' : [],
                'inputs' : [],
                'docs' : [],
                'docstack' : [],
                'modeldocs' : [],
                'tags' : {},
                'sources' : sources,
                'extern' : [],
           }
    
    # independent variable is always at index 0
    declare_symbol(find_independent(merged, independent), work)
    
    for item in merged:
        {
            'reaction' : process_reaction,
            'algeqn' : process_algeqn,
            'diffeqn' : process_diffeqn,
            'assign' : process_assign,
            'constraint' : process_constraint,
            'EMBEDDED' : process_embedded,
            'version' : process_version,
            'output' : process_output,
            'input' : process_input,
            'extern' : process_extern,
            'import' : ignore_silent,
            'independent' : ignore_silent,
            'DOC' : process_doc
        }.get(item[0], ignore_item)(item, work)
    
    transform_reactions(work)
    
    # consolidate global dependencies
    for name in work['symbols'].keys():
    	recurse_dependencies(name, set(), set(), work['symbols'])

    # assess whether a symbol depends on Y changes (made by solver)
    # only parameter updates (specified by user)
    rootset = set(work['roots'])
    for name in work['symbols']:
        if name in work['roots']:
            pass
        elif work['symbols'][name]['depends'] & rootset:
            work['intermeds'].append(name)
        else:
            work['params'].append(name)
        
    work['assignments'] = sort_assignments(work)
    
    finalise_outputs(work)
    finalise_externs(work)
    
    for name in set( work['roots'] + work['outputs'] ):
        work['required'].add(name)
        work['required'] = work['required'] | work['symbols'][name]['depends']
    
    work['unused'] = set(work['symbols'].keys()) - work['required'] - set(work['roots'])
    
    work['known'] = work['functions'] & STD_FUNCS
    work['unknown'] = work['functions'] - STD_FUNCS
        
    postprocess_docs(work)

    return work

# at the moment this is just a hack to handle one special case
# more considered doc compiling will be dealt with later (and probably elsewhere)
def postprocess_docs(work):
    for name in work['symbols']:
        symbol = work['symbols'][name]
        docs = symbol['docs']
        for line in docs:
            if line.startswith('+'):
                symbol['tags'].extend(line.strip('+').strip().split())
            elif line.startswith('$'):
                symbol['latex'] = line.strip('$').strip()
            elif line.startswith('~'):
                symbol['units'] = line.strip('~').strip()
        
        for tag in symbol['tags']:
            if tag in work['tags']:
                work['tags'][tag].append(name)
            else:
                work['tags'][tag] = [name]

# identify independent variable -- only first declaration applies
def find_independent(merged, default):
    independent = None
    for item in merged:
        if item[0] == 'independent':
            if independent is None:
                independent = item[1]
            else:
                logger.warn('Ignoring additional @independent directive: ' + item[1])
    if independent is None:
        return default
    return independent


# recursively consolidate all dependencies for all symbols
# this is pretty clunky and probably doing a lot of redundant work
# especially given that the results are of marginal utility
def recurse_dependencies(name, parents, done, symbols):
    if name in parents:
       if not symbols[name]['circular']:
           logger.detail('Circular dependency found for ' + name)
           symbols[name]['circular'] = True
    elif symbols[name]['circular']:
       logger.detail('Previous circularity noted for ' + name)
    else:
       for dep in symbols[name]['depends']:
           if dep in done:
               symbols[name]['depends'] = symbols[name]['depends'] | symbols[dep]['depends']
           else:
               symbols[name]['depends'] = (symbols[name]['depends']
                   | recurse_dependencies(dep, parents | set([name]), done, symbols))
        
    done = done | set([name])
    return symbols[name]['depends']


# sort assignment expressions into four groups:
# - independent for initialisation time
# - dependents ordered for overall initialisation time
# - parameters ordered for step initialisation time
# - dependents ordered for solver runtime
def sort_assignments(work):
    independent = []
    ind_expr = []
    dependent_init = []
    init_expr = []
    dependent_step = []
    step_expr = []
    dependent_run = []
    run_expr = []
    symbols = work['symbols']
    
    for name in work['assigned']:
        init, run = choose_assignments(symbols[name])
        if len(init['depends']) > 0:
            dependent_init.append(name)
            init_expr.append(init)
        else:
            independent.append(name)
            ind_expr.append(init)
        if run:
            if name in work['intermeds']:
                dependent_run.append(name)
                run_expr.append(run)
            else:
                dependent_step.append(name)
                step_expr.append(run)
        else:
            # intermeds is filled before we've determined
            # whether there's any runtime assignment to do
            # - now correct any earlier misapprehensions...
            if name in work['intermeds']:
                work['intermeds'].remove(name)
                if name not in work['params']:
                    work['params'].append(name)
    
    result = { 'independent': { 'names':independent, 'exprs':ind_expr } }
    
    names, exprs = dependency_sort(dependent_init, init_expr)
    result['dependent'] = { 'names': names, 'exprs': exprs }
    names, exprs = dependency_sort(dependent_step, step_expr)
    result['step'] = { 'names': names, 'exprs': exprs }
    names, exprs = dependency_sort(dependent_run, run_expr)
    result['runtime'] = { 'names':names, 'exprs': exprs }
    
    return result

# sort a matched pair of lists into dependency order
def dependency_sort(names, exprs):
    # this machine kills infinite loops (I hope)
    stopper = {}
    ordered_names = []
    ordered_exprs = []
    
    while names:
        name = names[0]
        del names[0]
        expr = exprs[0]
        del exprs[0]
        
        if len(names) >= stopper.get(name, len(names)+1):
            # we're now going around in circles
            logger.error('Unresolved circular dependency in assignments (at symbol ' \
                          + name + '), model may not non-viable')
            ordered_names.append(name)
            ordered_names += names
            ordered_exprs.append(expr)
            ordered_exprs += exprs
            return ordered_names, ordered_exprs
        
        stopper[name] = len(names)
            
        for dep in expr['depends']:
            if dep in names:
                names.append(name)
                exprs.append(expr)
                break
        
        if name not in names:
            ordered_names.append(name)
            ordered_exprs.append(expr)
    
    return ordered_names, ordered_exprs


# choose (guess) the relevant assignment expressions for initialisation and runtime
def choose_assignments(symbol):
    assigns = symbol['assigns']
    if len(assigns) == 1:
        if assigns[0]['init'] or len(assigns[0]['depends']) == 0:
            return assigns[0], False
        else:
            return assigns[0], assigns[0]
    
    if len(assigns) > 2:
        logger.warn('Warning: too many assignments for symbol ' + symbol['id'] + ':')
        logger.message(assigns, True)
    
    lo = 1e6
    hi = -1
    
    init = False
    noinit = False
    
    # we use a rule of thumb that the expression with fewer dependencies is
    # the initialisation; in the case of a tie, we take the later one as the init
    # (which is why we have <= vs > in the if clauses below)
    for ass in assigns:
        if ass['init']:
            init = ass
        else:
            noinit = ass
        
        ndeps = len(ass['depends'])
        if ndeps <= lo:
            lo = ndeps
            lo_expr = ass
        if ndeps > hi:
            hi = ndeps
            hi_expr = ass
    
    if init:
        return init, noinit
    
    if hi == lo:
        logger.warn('Ambiguous dependencies in assignment for ' + symbol['id'])
    
    return lo_expr, hi_expr


# unrecognised items and those we don't deal with yet (notably DOC)
def ignore_item(item, work):
    logger.detail("Ignoring item: " + item[0])

# items we recognise but do nothing with
def ignore_silent(item, work):
    pass

def declare_symbol(name, work):
    if name in work['symbols']:
        symbol = work['symbols'][name]
    else:
        symbol = { 'id' : name,
                   'depends' : set(),
                   'conflicts':0,
                   'assigns':[],
                   'diffs':[],
                   'algs':[],
                   'constraints':[],
                   'circular': False,
                   'index':len(work['symbols']),
                   'docs':[],
                   'tags':[] }
        work['symbols'][name] = symbol
        work['symlist'].append(name)
        logger.detail("Created symbol '" + name + "' at index %d" % work['symbols'][name]['index'])
    return symbol

# process documentation comments
# for the moment we just stash them, but...
def process_doc(item, work):
    work['docs'].append(item[1])
    
    # we normally attach doc comments to the left hand symbol of a following eq
    # but we can instead attach to an arbitrary list of symbols using an @ line...
    # further, if no targets are specified, we attach the doc comments to the model itself
    if item[1].startswith('@'):
        targets = item[1].strip('@').split()
        if targets:
            for target in targets:
                sym = declare_symbol(target, work)
                sym['docs'].extend(work['docstack'])
        else:
            work['modeldocs'].extend(work['docstack'])        
        work['docstack'] = []
    else:
        work['docstack'].append(item[1])

def process_version(item, work):
    if ( work['version'] ):
        logger.warn('Ignoring additional @version directive: ' + item[1])
    else:
        logger.message('Model version is: ' + item[1])
        work['version'] = item[1]

# set fields to output by default
# note that this does not create symbols -- fields which are listed as outputs
# but never get actually created anywhere will be ignored
def process_output(item, work):
    logger.detail('Appending default output fields:' + str(item[1:]))    
    # only include each field once
    for id in item[1:]:
        if id not in work['outputs']:
            work['outputs'].append(id)

# finalise the output fields list
def finalise_outputs(work):
    logger.warn(work['outputs'], True)
    present = [ x for x in work['outputs'] if x in work['symbols']]
    if present:
        work['outputs'] = present
    else:
        work['outputs'] = work['roots']

# mark fields as inputs
# as with output, this does not create symbols
def process_input(item, work):
    logger.detail('Appending input fields:' + str(item[1:]))
    # only include each field once
    work['inputs'].extend([x for x in item[1:] if x not in work['inputs']])

# mark fields as external
# as with output, this does not create symbols
def process_extern(item, work):
    logger.detail('Appending extern fields:' + str(item[1:]))
    # only include each field once
    work['extern'].extend([x for x in item[1:] if x not in work['extern']])

# finalise the external fields list
# fields are only considered external if they exist but are not assigned in the model
def finalise_externs(work):
    logger.message(work['extern'], True)
    work['extern'] = [ x for x in work['extern'] if x in work['symbols'] and x not in work['assigned'] ]

# processing for diff eqns, algebraics and assignments is similar,
# but there are enough differences that they get separate functions
def process_diffeqn(item, work):
    target = item[1]
    logger.message("Processing differential equation for variable: " + target)
    symbol = declare_symbol(target, work)
    if work['docstack']:
        symbol['docs'].extend(work['docstack'])
        work['docstack'] = []
    
    if target in work['roots']:
        symbol['conflicts'] = symbol['conflicts'] + 1
    else:
        work['roots'].append(target)
    
    if target not in work['diffs']:
        work['diffs'].append(target)
    
    i_expr, expr, depends = process_mathterm(item[2][1], work)
    symbol['diffs'].append({'expr':expr, 'i_expr':i_expr, 'depends':depends, 'mathterm':item[2][1]})
    symbol['depends'] |= depends
    
    # process auxiliary terms, if any
    auxterm = item[4]
    offset = 1
    auxes = []
    while len(auxterm) >= offset + 3:
        mass = auxterm[offset + 1]
        if auxterm[offset] == '-':
            mass = -1 * mass
        auxes.append((mass, auxterm[offset + 2]))
        offset = offset + 3
    work['auxiliaries'][item[1]] = auxes
    if offset > 1:
        work['diagonal'] = False

def process_algeqn(item, work):
    target = item[1]
    logger.message("Processing algebraic relation for variable: " + target)
    symbol = declare_symbol(target, work)
    if work['docstack']:
        symbol['docs'].extend(work['docstack'])
        work['docstack'] = []
    if target in work['roots']:
        symbol['conflicts'] = symbol['conflicts'] + 1
    else:
        work['roots'].append(target)
    
    if target not in work['algs']:
        work['algs'].append(target)
    
    i_expr, expr, depends = process_mathterm(item[2][1], work)
    symbol['algs'].append({'expr':expr, 'i_expr':i_expr, 'depends':depends, 'mathterm':item[2][1]})
    symbol['depends'] |= depends

def process_assign(item, work):
    target = item[1]
    logger.detail("Processing assignment to variable: " + target)
    symbol = declare_symbol(target, work)
    if work['docstack']:
        symbol['docs'].extend(work['docstack'])
        work['docstack'] = []
    work['assigned'].add(target)
    
    i_expr, expr, depends = process_mathterm(item[2][1], work)
    symbol['assigns'].append({'expr':expr, 'i_expr':i_expr, 'depends':depends, 'init':item[4], 'mathterm':item[2][1]})
    symbol['depends'] |= depends

def process_constraint(item, work):
    item = item[1]
    kind = item[0]
    if ( kind == 'softbound' ): item = item[1]
    symbol = declare_symbol(item[1], work)
    if work['docstack']:
        symbol['docs'].extend(work['docstack'])
        work['docstack'] = []
    
    # declarations are inverted for testing
    test = {'<':'>=', '<=':'>', '>':'<=', '>=':'<'}.get(item[2], 'ERROR')
    i_expr, expr, deps = process_mathterm(item[3][1], work)
    symbol['constraints'].append({'kind':kind, 'test':test, 'expr':expr,
                                  'i_expr':i_expr, 'depends':deps, 'mathterm':item[3][1]})
    symbol['depends'] |= deps

# convert a reaction to standard form and add to the workspace
def process_reaction(item, work):
    logger.message("Processing reaction '" + item[2][1] + "' of type: " + item[1])
    {
        'influx' : process_flux,
        'outflux' : process_flux,
        'oneway' : process_oneway,
        'twoway' : process_twoway
    }.get(item[1], unknown_reaction)(item, work)

# reactions with only one side are treated similarly, but not
# *exactly* the same
def process_flux(term, work):
    tag = term[1]    
    logger.detail('Processing ' + tag + ' reaction')
    label = term[2][1]
    if label == '': label = default_label(tag + '__')
    while label in work['reactions'].keys():
        newlabel = default_label(tag + '__')
        logger.warn("Duplicate reaction label '" + label
                     + "', substituting '" + newlabel + "'")
        label = newlabel
    
    # I have no idea whether this is reasonable, but:
    # outflux reactions have an LHS and can (if necessary)
    # be given MA rates; influx reactions don't and can't
    if tag == 'outflux':
        terms = process_chemterm(term[3], work, -1)
        rate = process_rateterm(term[4], work, terms)
        lhs = terms
        rhs = []
    else:
        terms = process_chemterm(term[3], work, 1)
        rate = process_rateterm(term[4], work, None)
        lhs = []
        rhs = terms

    work['reactions'][label] = { 'type' : tag,
                                 'terms' : terms,
                                 'rate' : rate,
                                 'lhs' : lhs,
                                 'rhs': rhs,
                                 'ratespec': term[4] }
    consolidate_chems(work['reactions'][label])

def process_oneway(term, work):
    label = term[2][1]
    logger.detail("Processing oneway reaction '" + label + "'")
    if label == '': label = default_label('oneway__')
    while label in work['reactions'].keys():
        newlabel = default_label('oneway__')
        logger.warn("Duplicate reaction label '" + label
                     + "', substituting '" + newlabel + "'")
        label = newlabel
    
    lhs = process_chemterm(term[3], work, -1)
    rhs = process_chemterm(term[4], work, 1)
    
    rate = process_rateterm(term[5], work, lhs)
    
    work['reactions'][label] = { 'type' : 'oneway',
                                 'terms' : lhs + rhs,
                                 'rate' : rate,
                                 'lhs' : lhs,
                                 'rhs' : rhs,
                                 'ratespec': term[5] }
    consolidate_chems(work['reactions'][label])

# twoway reactions are just broken into separate forward and backward oneways
def process_twoway(term, work):
    label = term[2][1]
    logger.detail("Processing twoway reaction '" + label + "'")
    if label == '': label = default_label('twoway__')
    
    forward = ('reaction',
               'oneway',
               ('label', label + '_forward'),
               term[3],
               term[4],
               term[5])
    reverse = ('reaction',
               'oneway',
               ('label', label + '_reverse'),
               term[4],
               term[3],
               term[6])
    
    process_oneway(forward, work)
    process_oneway(reverse, work)

# this shouldn't happen
def unknown_reaction(item, work):
    logger.message("Ignoring unknown reaction type: " + item[1])

# it is convenient to have the terms information in lookup form
def consolidate_chems(reaction):
    terms = reaction['terms']
    chems = {}
    for term in terms:
        chems[term['chem']] = {'depends':term['depends'],
                                'stoich':term['stoich'],
                                'i_stoich':term['i_stoich'],
                                'mathterm':term.get('mathterm', '[ERROR]')}
    reaction['chems'] = chems

# once all reactions (and other relevant terms) have been processed,
# transform the whole system to ODEs, one per chemical
def transform_reactions(work):
    reacs = work['reactions']
    
    if len(reacs) > 0:
        logger.message('Transforming reactions to ODEs')
    else:
        return

    chems = work['chemicals']
    syms = work['symbols']
    roots = work['roots']
    
    # construct an ODE for each chemical
    for chem in chems.keys():
        sym = declare_symbol(chem, work)
        if ( chem in roots ):
            sym['conflicts'] = sym['conflicts'] + 1
        else:
            roots.append(chem)
        work['diffs'].append(chem)
        if chem not in work['auxiliaries']:
            work['auxiliaries'][chem] = []
        
        expr = ''
        i_expr = ()
        deps = set()
        mathterm = ()
        
        for reactlabel in reacs.keys():
            reaction = reacs[reactlabel]
            if chem in reaction['chems'].keys():
                deps |= reaction['rate']['depends']
                deps |= reaction['chems'][chem]['depends']
                
                if len(expr) > 0: expr = expr + ' + '
                if len(i_expr) > 0: i_expr = i_expr + (('literal',' + '),)
                expr = expr + ( '(' + reaction['chems'][chem]['stoich']
                                + '*' + reaction['rate']['expr'] + ')' )
                i_expr = i_expr + (('literal','('),) \
                                + reaction['chems'][chem]['i_stoich'] \
                                + (('literal','*'),) \
                                + reaction['rate']['i_expr'] \
                                + (('literal',')'),)
                
                subterm = ( 'arithmetic',
                            '*',
                            ('mathterm', reaction['chems'][chem]['mathterm']),
                            ('mathterm', reaction['rate']['mathterm']) )
                if mathterm:
                    mathterm = ( 'arithmetic',
                                 '+',
                                 ('mathterm', mathterm),
                                 ('mathterm', subterm) )
                else:
                    mathterm = subterm
                
        
        sym['depends'] |= deps
        sym['diffs'].append({'depends':deps, 'expr':expr, 'i_expr':i_expr, 'mathterm':mathterm})


# multiplier indicates whether terms are reactants or products
# conventionally will be -1 for LHS terms and +1 for RHS ones
def process_chemterm(term, work, multiplier):
    logger.detail("Processing chemterm")
    terms = []
    idx = 1
    while idx < len(term):
        logger.detail('iterating term: ' + str(term[idx]) + ', ' + str(term[idx+1]))
        i_expr, expr, deps = process_mathterm(term[idx][1], work)
        unmod = expr
        i_unmod = i_expr
        mathterm = term[idx][1]
        
        # # this is a thoroughly dodgy bit of hackery
        # # may change in line with better expr handling
        if ( multiplier != 1 ):
            expr = '(' + str(multiplier) + '*' + expr + ')'
            i_expr = (('literal','(' + str(multiplier) + '*'),) + i_expr + (('literal',')'),)
            mathterm = ('arithmetic', '*', ('mathterm', decimal.Decimal('-1')), term[idx])
        
        chem = process_chemical(term[idx+1], work)
        terms.append({'stoich': expr, 'chem':chem, 'unmod':unmod,
                      'i_stoich': i_expr, 'i_unmod':i_unmod,
                      'mathterm_unmod':term[idx][1], 'mathterm':mathterm,
                     'depends': deps|work['symbols'][chem]['depends']})
        idx = idx + 2
    return terms

def process_chemical(term, work):
    logger.detail("Processing chemical: " + str(term))
    if len(term) == 2:
        chem = term[1]
        work['chemicals'][chem] = None
        symbol = declare_symbol(chem, work)
    else:
        chem = term[1] + '_' + term[2]
        work['chemicals'][chem] = term[2]
        declare_symbol(term[2], work)
        symbol = declare_symbol(chem, work)
        symbol['depends'] = symbol['depends'] | set([term[2]])
    
    # automatic non-negativity constraint on chemicals
    if NON_NEGATIVE not in symbol['constraints']:
        symbol['constraints'].append(NON_NEGATIVE)
    
    return chem

def process_rateterm(term, work, lhs):
    return {
               'explicit' : process_explicit_rate,
               'MA' : process_MA_rate,
               'MM' : process_MM_rate
           }.get(term[1], unknown_rate_type)(term, work, lhs)

def process_explicit_rate(term, work, lhs):
    logger.detail("Processing explicit rateterm")
    if len(term[2]) > 2:
        logger.warn("More than 1 rate term supplied, ignoring excess")
    
    i_expr, expr, deps = process_mathterm(term[2][1][1], work)
    return { 'i_expr':i_expr, 'expr':expr, 'depends':deps, 'mathterm':term[2][1][1] }
    
def process_MA_rate(term, work, lhs):
    logger.detail("Processing mass action rateterm")
    if len(term[2]) > 2:
        logger.detail("More than 1 rate term supplied, extras will be taken as concentration exponents")
    
    i_expr, expr, deps = process_mathterm(term[2][1][1], work)
    mathterm = term[2][1][1]
    
    if lhs is None:
        logger.detail("Reaction has no LHS, omitting concentration dependence")
    else:
        num = []
        denom = []
        i_num = []
        i_denom = []
        
        m_num = ()
        m_denom = ()
        
        offset_exp_idx = 2
        for chem in lhs:
            name = chem['chem']
            
            if len(term[2]) > offset_exp_idx:
                i_exponent, exponent, exp_deps = process_mathterm(term[2][offset_exp_idx][1], work)
                m_exponent = term[2][offset_exp_idx][1]
                
                num.append('pow(' + name + ',' + exponent + ')')
                i_num.append( (('literal','pow('),) + (('symbol', name),) + (('literal',','),) + i_exponent + (('literal',')'),) )
                deps = deps | exp_deps
                
                m_sub = ('arithmetic',
                         '^',
                         ('mathterm', name),
                         ('mathterm', m_exponent))
                
                if m_num:
                    m_num = ('arithmetic',
                             '*',
                             ('mathterm', m_num),
                             ('mathterm', m_sub))
                else:
                    m_num = m_sub
            else:
                num.append(name)
                i_num.append((('symbol',name),))
                
                if m_num:
                    m_num = ('arithmetic',
                             '*',
                             ('mathterm', m_num),
                             ('mathterm', name))
                else:
                    m_num = name
            
            if work['chemicals'][name] is not None:
                compartment = work['chemicals'][name]
                denom.append(compartment)
                i_denom.append((('symbol',compartment),))
                
                if m_denom:
                    m_denom = ('arithmetic',
                               '*',
                               ('mathterm', m_denom),
                               ('mathterm', compartment))
                else:
                    m_denom = compartment
            
            deps = deps | set([name]) | work['symbols'][name]['depends']
            
            offset_exp_idx += 1
        
        factor = '(' + '*'.join(num) + ')'
        
        i_factor = i_num[0]
        for ifx in i_num[1:]:
            i_factor = i_factor + (('literal','*'),) + ifx
        
        i_factor = (('literal','('),) + i_factor + (('literal',')'),)
        
        m_factor = m_num
        
        if len(denom) > 0:
            factor = factor + '/(' + '*'.join(denom) + ')'
            
            i_divisor = i_denom[0]
            for idn in i_denom[1:]:
                i_divisor = i_divisor + (('literal','*'),) + idn
            i_factor = i_factor + (('literal','/('),) + i_divisor + (('literal', ')'),)
            
            m_factor = ('arithmetic',
                        '/',
                        ('mathterm', m_factor),
                        ('mathterm', m_denom))
        
        expr = '(' + expr + '*' + factor + ')'
        i_expr = (('literal','('),) + i_expr + (('literal','*'),) \
                 + i_factor + (('literal',')'),)
                 
        mathterm = ('arithmetic',
                    '+',
                    ('mathterm', mathterm),
                    ('mathterm', m_factor))
    
    return { 'i_expr':i_expr, 'expr':expr, 'depends':deps, 'mathterm':mathterm }

# this is the most complicated rate term we support, requiring terms to
# be raised to the power of the stoichiometry
def process_MM_rate(term, work, lhs):
    logger.detail("Processing Michaelis-Menten rateterm")
    arglist = term[2]
    if len(arglist) != len(lhs) + 2: # one for 'arglist' + one for Vmax
        logger.warn("Incorrect parameters for Michaelis-Menten rate term, skipping!")
        return { 'i_expr':('error','FAILED'), 'expr':'FAILED', 'depends':set() }
    
    i_num = []
    i_denom = []
    num = []
    denom = []
    
    i_expr, expr, deps = process_mathterm(arglist[1][1], work)
    num.append(expr)
    i_num.append(i_expr)
    
    m_num = arglist[1][1]
    m_denom = ()
    
    for idx in range(len(lhs)):
        logger.detail(idx)
        i_Km_expr, Km_expr, km_deps = process_mathterm(arglist[idx+2][1], work)
        deps = deps | km_deps | lhs[idx]['depends']
        
        m_Km = arglist[idx+2][1]
        
        # explicitly add Km to dependencies if it is a symbol in its own right
        # since otherwise the dependency won't get registered
        if Km_expr in work['symbols'].keys():
            deps = deps | set([Km_expr])
        
        chem = lhs[idx]['chem']
        i_chem = (('symbol',chem),)
        stoich = lhs[idx]['unmod']   # we only want the original value without the -1 multiplier
        i_stoich = lhs[idx]['i_unmod']
        
        m_stoich = lhs[idx]['mathterm_unmod']
        
        # x^1 is obviously just x...
        if stoich == '1':
            conc_pwr = chem
            Km_pwr = Km_expr
            i_conc_pwr = i_chem
            i_Km_pwr = i_Km_expr
            
            m_conc_pwr = chem
            m_Km_pwr = m_Km
        else:
            conc_pwr = 'pow(' + chem + ',' + stoich + ')'
            Km_pwr = 'pow(' + Km_expr + ',' + stoich + ')'
            i_conc_pwr = (('literal','pow('),) + i_chem + (('literal',','),) + i_stoich + (('literal',')'),)
            i_Km_pwr = (('literal','pow('),) + i_Km_expr + (('literal',','),) + i_stoich + (('literal',')'),)
            
            m_conc_pwr = ('arithmetic',
                          '^',
                          ('mathterm', chem),
                          ('mathterm', m_stoich))
            m_Km_pwr = ('arithmetic',
                        '^',
                        ('mathterm', m_Km),
                        ('mathterm', m_stoich))
        
        num.append(conc_pwr)
        denom.append('(' + Km_pwr + '+' + conc_pwr + ')')
        i_num.append(i_conc_pwr)
        i_denom.append((('literal', '('),) + i_Km_pwr + (('literal','+'),) + i_conc_pwr + (('literal',')'),))
        
        m_num = ('arithmetic',
                 '*',
                 ('mathterm', m_num),
                 ('mathterm', m_conc_pwr))
        
        m_sub = ('arithmetic',
                 '+',
                 ('mathterm', m_Km_pwr),
                 ('mathterm', m_conc_pwr))
        
        if m_denom:
            m_denom = ('arithmetic',
                       '*',
                       ('mathterm', m_denom),
                       ('mathterm', m_sub))
        else:
            m_denom = m_sub
    
    num_expr = '*'.join(num)
    denom_expr = '*'.join(denom)
    expr = '((' + num_expr + ')/(' + denom_expr + '))'
    
    i_num_expr = i_num[0]
    for iex in i_num[1:]:
        i_num_expr = i_num_expr + (('literal','*'),) + iex
    i_denom_expr = i_denom[0]
    for iex in i_denom[1:]:
        i_denom_expr = i_denom_expr + (('literal','*'),) + iex

    i_expr = (('literal','(('),) + i_num_expr + (('literal',')/('),) \
             + i_denom_expr + (('literal','))'),)
    
    mathterm = ('arithmetic',
                '/',
                ('mathterm', m_num),
                ('mathterm', m_denom))
    
    return { 'i_expr':i_expr, 'expr':expr, 'depends':deps, 'mathterm': mathterm }


def unknown_rate_type(term, work, lhs):
    logger.warn("Unknown rate type: '" + term[1] + "' -- treating as explicit")
    return process_explicit_rate(term, work, lhs)
    
# embeds just get stashed blindly, we don't do any analysis on them
def process_embedded(item, work):
    logger.detail("Processing embedded code fragment")
    work['embeds'].append(item[1])

#----------------------------------------------------------------------

# expression handling functions -- these all return I_EXPR, EXPR, DEPENDS

def process_mathterm(term, work):
    logger.detail("Processing mathterm: " + str(term))
    if isinstance(term, decimal.Decimal):
        return (('literal', str(float(term))),), str(term), set()
    if isinstance(term, str):
        declare_symbol(term,work)
        return (('symbol', term),), term, set([term])
    
    if not isinstance(term, tuple):
        return (('error','ERROR'),), 'ERROR', set()
    
    return {
            'function' : process_function,
            'conditional' : process_conditional,
            'arithmetic' : process_binop
           }.get(term[0], unknown_mathterm)(term, work)

def unknown_mathterm(term, work):
    # recursive catcher for errors with my dumb calling convention
    if ( term[0] == 'mathterm' ):
        return process_mathterm(term[1], work)
    return (('error','UNKNOWN'),), 'UNKNOWN', set()
    
def process_function(term, work):
    work['functions'] = work['functions'] | set([term[1]])
    i_argexpr, argexpr, argdeps = process_arglist(term[2], work)
    i_expr = (('literal',term[1]), ('literal','(')) + i_argexpr + (('literal',')'),)
    expr = term[1] + '(' + argexpr + ')'
    return i_expr, expr, argdeps

def process_arglist(arglist, work):
    if len(arglist) < 2:
        return '', '', set()
    
    i_expr, expr, deps = process_mathterm(arglist[1][1], work)
    idx = 2
    while idx < len(arglist):
        i_nextExpr, nextExpr, nextDeps = process_mathterm(arglist[idx][1], work)
        i_expr = i_expr + (('literal',', '),) + i_nextExpr
        expr = expr + ', ' + nextExpr
        deps = deps | nextDeps
        idx += 1
    
    return i_expr, expr, deps

def process_conditional(term, work):
    i_condExpr, condExpr, condDeps = process_binop(term[1], work)
    i_yesExpr, yesExpr, yesDeps = process_mathterm(term[2][1], work)
    i_noExpr, noExpr, noDeps = process_mathterm(term[3][1], work)
    
    i_expr = (('literal','('),) + i_condExpr + (('literal',' ? '),) \
             + i_yesExpr + (('literal', ' : '),) + i_noExpr + (('literal',')'),)
    expr = '(' + condExpr + ' ? ' + yesExpr + ' : ' + noExpr + ')'
    
    return i_expr, expr, condDeps | yesDeps | noDeps

# logical and arithmetic binary operations are all handled the same way
def process_binop(term, work):
    i_expr1, expr1, deps1 = process_mathterm(term[2][1], work)
    i_expr2, expr2, deps2 = process_mathterm(term[3][1], work)
    
    # special case '^', since it means something else in C
    expr = '(' + expr1 + term[1] + expr2 + ')'
    if term[1] == '^':
        i_expr = (('literal','pow('),) + i_expr1 + (('literal', ', '),) + i_expr2 + (('literal', ')'),)
    else:
        i_expr = (('literal', '('),) + i_expr1 + (('literal', term[1]),) + i_expr2 + (('literal',')'),)
    
    return i_expr, expr, deps1 | deps2

