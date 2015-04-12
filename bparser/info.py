import sys
import os
import string
import logger
import pprint
import argparse
import os.path
import re
import datetime, time

# we import Decimal locally in order to be able to 'eval' any
# relevant entries in a BCMPL file
from decimal import Decimal

import doc_html
import doc_latex
import doc_text

CONFIG = { 'name' : 'unknown',
           'unused' : True,
           'graph-exclude-unused': False,
           'graph-exclude-init': False,
           'graph-exclude-clusters': False,
           'graph-exclude-self': True,
           'graph-exclude-params':False,
           'graph-horizontal':False,
           'outdir' : '.',
           'no-graph' : False,
           'log-info' : False,
           'debug' : False,
           'input-makes-intermed':True,
           'text' : False,
           'html' : False,
           'latex' : False,
           'css-embed' : True,
           'css-src' : None,
           'eq-align': False,
           'latex-display-style': True,
           'latex-include-code': True
          }

# functions to output information about the structure of a model

# dump a bunch of model info for debugging purposes
def logModelInfo(model, config):
    logger.detail('\n\n** work **\n', False)
    logger.detail(model)
    
    # log the main actual equation system
    logger.message("\n\n** equations **")
    for name in model['diffs']:
        sym = model['symbols'][name]
        if sym['conflicts'] > 0: tag = '[CONFLICT-?] '
        else: tag = ''
        
        lhs = name + "'"
        for aux in model['auxiliaries'][name]:
            mass = aux[0]
            if mass < 0:
               mass = mass * -1
               op = ' - '
            else:
               op = ' + '
            lhs = lhs + op + str(mass) + ' ' + aux[1] + "'"
        
        for diff in sym['diffs']:
            logger.message(tag + lhs + ' = ' + diff['expr'])
    
    for name in model['algs']:
        sym = model['symbols'][name]
        if sym['conflicts'] > 0: tag = '[CONFLICT-?] '
        else: tag = ''
        for alg in sym['algs']:
            logger.message(tag + 'f(' + name + ') : 0 = ' + alg['expr'])

    # log dependency info
    logger.message("\n\n** dependency analysis **")
    logger.message("\nThe following solver variables are used in the model:")
    for name in sorted(model['diffs'], key=str.lower): logger.message(name)
    for name in sorted(model['algs'], key=str.lower): logger.message(name)
    
    logger.detail("\nThe following intermediate variables or parameters are used by the model:", False)
    for name in sorted(model['required'], key=str.lower):
        if name in model['assigned']:
            logger.detail(name + ' (assigned)')
        else:
            logger.detail(name + ' (unassigned)')
    
    if model['inputs']:
        logger.message('\nThe following symbols are declared as inputs:')
        for name in sorted(model['inputs'], key=str.lower):
            logger.message(name)
    
    if model['params']:
        logger.message('\nThe following symbols are parameters, independent of the solver variables:')
        for name in sorted(model['params'], key=str.lower):
            logger.message(name)
    
    if model['intermeds']:
        logger.message('\nThe following symbols are intermediates, with solver variable dependencies:')
        for name in sorted(model['intermeds'], key=str.lower):
            logger.message(name)
    
    if model['unused']:
        logger.message('\nThe following intermediate variables or parameters are declared but unused:')
        for name in sorted(model['unused'], key=str.lower): logger.message(name)
        if config['unused']:
            logger.message('(NB: unused variables will still be calculated)')
        else:
            logger.message('(NB: unused variables will NOT be calculated)')
            
    undoc = [ x for x in model['symbols'] if not [y for y in model['symbols'][x]['docs'] if not y.startswith('+')] ]
    if undoc:
        logger.message('\nThe following symbols are not documented:')
        for name in sorted(undoc, key=str.lower): logger.message(name)

    unassigned = set(model['symlist']) - model['assigned']
    if unassigned:
        logger.warn('\nThe following symbols are never explicitly assigned (will default to 0):')
        for name in sorted(unassigned, key=str.lower):
            logger.warn(name)

    if model['extern']:
        logger.warn('\nThe following external dependencies are declared but unsatisfied:\n')
        for name in sorted(model['extern'], key=str.lower): logger.warn(name)

    if model['unknown']:
        logger.warn("\nThe model makes use of the following non-standard functions:")
        for name in model['unknown']: logger.warn(name)
    
    # examine circular dependencies
    logger.detail("\nCircular dependencies:")
    for name in model['symbols'].keys():
        if model['symbols'][name]['circular']:
            if name in model['roots']:
                logger.detail(name + " (is a solver var)")
            elif name in model['unused']:
                logger.detail(name + ' (unused)')
            else:
                LHS = model['symbols'][name]['depends'] & set(model['roots'])
                if len(LHS) == 0:
                    logger.detail(name + " (no LHS dependencies)")
                else:
                    logger.detail(name + ' ' + str(LHS))
    
    logger.message('')

    logger.message('** summary for model %s **' % config['name'])
    logger.message('%d model variables (%d differential, %d algebraic)' % (len(model['roots']), len(model['diffs']), len(model['algs'])))
    logger.message('%d intermediate variables (%d unused)' % (len(model['intermeds']), len([x for x in model['intermeds'] if x in model['unused']])))
    logger.message('%d parameters (%d unused)' % (len(model['params']), len([x for x in model['params'] if x in model['unused']])))
    logger.message('%d unsatisfied external dependencies\n' % len(model['extern']))

    logger.message('')

# similar to the above, but generating a string instead of logging
def modelInfo(model, config):
    result = '** summary for model %s **\n' % config['name']
    result += '%d model variables (%d differential, %d algebraic)\n' % (len(model['roots']), len(model['diffs']), len(model['algs']))
    result += '%d intermediate variables (%d unused)\n' % (len(model['intermeds']), len([x for x in model['intermeds'] if x in model['unused']]))
    result += '%d parameters (%d unused)\n' % (len(model['params']), len([x for x in model['params'] if x in model['unused']]))
    result += '%d unsatisfied external dependencies\n' % len(model['extern'])
    
    result += '\n** equations **\n'
    
    for name in model['diffs']:
        sym = model['symbols'][name]
        if sym['conflicts'] > 0: tag = '[CONFLICT-?] '
        else: tag = ''
        
        lhs = name + "'"
        for aux in model['auxiliaries'][name]:
            mass = aux[0]
            if mass < 0:
               mass = mass * -1
               op = ' - '
            else:
               op = ' + '
            lhs = lhs + op + str(mass) + ' ' + aux[1] + "'"
        
        for diff in sym['diffs']:
            result += tag + lhs + ' = ' + diff['expr'] + '\n'
    
    for name in model['algs']:
        sym = model['symbols'][name]
        if sym['conflicts'] > 0: tag = '[CONFLICT-?] '
        else: tag = ''
        for alg in sym['algs']:
            result += tag + 'f(' + name + ') : 0 = ' + alg['expr'] + '\n'

    # log dependency info
    result += '\n** dependency analysis **\n'
    result += 'The following solver variables are used in the model:\n'
    for name in sorted(model['diffs'], key=str.lower): result += name + '\n'
    for name in sorted(model['algs'], key=str.lower): result += name + '\n'

    if model['inputs']:
        result += '\nThe following symbols are declared as inputs:\n'
        for name in sorted(model['inputs'], key=str.lower):
            result += name + '\n'
    
    if model['params']:
        result += '\nThe following symbols are parameters, independent of the solver variables:\n'
        for name in sorted(model['params'], key=str.lower):
            result += name + '\n'
    
    if model['intermeds']:
        result += '\nThe following symbols are intermediates, with solver variable dependencies:\n'
        for name in sorted(model['intermeds'], key=str.lower):
            result += name + '\n'
    
    if model['unused']:
        result += '\nThe following intermediate variables or parameters are declared but unused:\n'
        for name in sorted(model['unused'], key=str.lower):  result += name + '\n'
    
    undoc = [ x for x in model['symbols'] if not [y for y in model['symbols'][x]['docs'] if not y.startswith('+')] ]
    if undoc:
        result += '\nThe following symbols are not documented:\n'
        for name in sorted(undoc, key=str.lower): result += name + '\n'
    
    unassigned = set(model['symlist']) - model['assigned']
    if unassigned:
        result += '\nThe following symbols are never explicitly assigned (will default to 0):\n'
        for name in sorted(unassigned, key=str.lower): result += name + '\n'

    if model['extern']:
        result += '\nThe following external dependencies are declared but unsatisfied:\n'
        for name in sorted(model['extern'], key=str.lower): result += name + '\n'

    if model['unknown']:
        result += '\nThe model makes use of the following non-standard functions:\n'
        for name in model['unknown']: result += name + '\n'
    
    return result

# write documentation in (for the moment) plain text format
def writeDoc(model, config):
    with open(os.path.join(config['outdir'], config['text']), 'w') as f:
        printHeader(f, model, config)
        printModelDescription(f, model, config)
        printDiffs(f, model, config)
        printAlgs(f, model, config)
        printIntermeds(f, model, config)
        printParameters(f, model, config)
        
def printHeader(file, model, config):
    print >> file, 'Model information for %s' % config['name']
    print >> file, 'Generated by BCMD bparser.info'
    print >> file, datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print >> file, ''

def printModelDescription(file, model, config):
    desc = '\n'.join([x for x in model['modeldocs'] if not (x.startswith('+') or x.startswith('@') or x.startswith('$'))])
    print >> file, desc
    print >> file, ''
    print >> file, '%d state variables (%d differential, %d algebraic)' % (len(model['roots']), len(model['diffs']), len(model['algs']))
    print >> file, '%d intermediate variables (%d unused)' % (len(model['intermeds']), len([x for x in model['intermeds'] if x in model['unused']]))
    print >> file, '%d parameters (%d unused)' % (len(model['params']), len([x for x in model['params'] if x in model['unused']]))
    print >> file, ''
    print >> file, '%d declared inputs, %d default outputs' % (len(model['inputs']), len(model['outputs']))
    print >> file, '%d tags' % len(model['tags'])
    
    print >> file, '\n'

def printDiffs(file, model, config):
    print >> file, '*** DIFFERENTIAL VARIABLES ***\n'        
    for name in sorted(model['diffs'], key=lambda s: s.lower()):
        printVar(name, file, model, config, ['Differential'])

def printAlgs(file, model, config):
    print >> file, '*** ALGEBRAIC VARIABLES ***\n'        
    for name in sorted(model['algs'], key=lambda s: s.lower()):
        printVar(name, file, model, config, ['Algebraic'])

def printIntermeds(file, model, config):
    print >> file, '*** INTERMEDIATE VARIABLES ***\n'        
    for name in sorted(model['intermeds'], key=lambda s: s.lower()):
        printVar(name, file, model, config, ['Intermediate'])

def printParameters(file, model, config):
    print >> file, '*** PARAMETERS ***\n'        
    for name in sorted(model['params'], key=lambda s: s.lower()):
        printVar(name, file, model, config, ['Parameter'])

def printVar(name, file, model, config, classes):
    if name in model['chemicals']: classes.append('Species')
    if name in model['inputs']: classes.append('Input')
    if name in model['outputs']: classes.append('Output')
    if name in model['unused']: classes.append('Unused')
    
    print >> file, '* %s (%s)' % (name, ', '.join(classes))
    
    sym = model['symbols'][name]
    if sym['diffs']:
        expr = sym['diffs'][0]
    elif sym['algs']:
        expr = sym['algs'][0]
    else:
        expr = [x for x in sym['assigns'] if not x['init']]
        if expr: expr = expr[0]

    if expr:
        print >> file, '  Expression: %s' % expr['expr']
        print >> file, '  Dependencies: %s' % ', '.join(sorted(expr['depends'], key=lambda s: s.lower()))
    
    init = [x for x in sym['assigns'] if x['init']]
    
    if init:
        print >> file, '  Initialiser: %s' % init[0]['expr']
        if init[0]['depends']:
            print >> file, '  Initialiser Dependencies: %s' % ', '.join(sorted(init[0]['depends'], key=lambda s: s.lower()))
    else:
        print >> file, '  Initialiser: Not specified, defaults to 0'
        
    if sym['tags']:
        print >> file, '  Tags: %s' % ', '.join(sorted(sym['tags'], key=lambda s: s.lower()))
    
    docs = [x for x in sym['docs'] if not (x.startswith('+') or x.startswith('@') or x.startswith('$'))]
    if docs:
        print >> file, '\n  %s' % '\n  '.join(docs)
    
    print >> file, '\n'
            
# generate the model dependency structure in GraphViz format
def generateGraphViz(model, config):
    # in CLI use this function might get called several times
    # -- stash the classification so we only have to do it once
    if model.get('classify', False):
        graph = model['classify']
    else:
        graph = classify(model, config)
        model['classify'] = graph
    
    if config['debug']:
        pprint.pprint(graph, stream=sys.stderr)
    
    NODE_STYLES = {
        'diff' : '[shape=doublecircle, fillcolor=orange, style="filled,solid", color=black]',
        'alg' : '[shape=doublecircle, fillcolor=olivedrab1, style="filled,solid", color=black]',
        'intermed' : '[shape=circle, fillcolor=lightskyblue, style="filled,solid", color=black]',
        'intermed-init' : '[shape=circle, fillcolor=lightskyblue, style="filled,solid", color=chocolate]',
        'intermed-unused' : '[shape=circle, fillcolor=lightskyblue, style="filled,dashed", color=black]',
        'intermed-init-unused' : '[shape=circle, fillcolor=lightskyblue, style="filled,dashed", color=black]',
        'input': '[shape=box, fillcolor=lightsalmon, style="filled,solid", color=black]',
        'output': '[shape=box, fillcolor=lemonchiffon, style="filled,solid", color=black]',
        'extern': '[shape=box, fillcolor="#dcffdc", style="filled,solid", color=black]',
        'param' : '[shape=box, fillcolor=lemonchiffon, style="filled,solid", color=salmon, fontsize=12]',
        'param-init' : '[shape=box, fillcolor=white, style="filled,solid", color=lightsalmon, fontsize=12]',
        'param-unused' : '[shape=box, fillcolor=lemonchiffon, style="filled,dashed", color=salmon, fontsize=12]',
        'param-init-unused' : '[shape=box, fillcolor=white, style="filled,dashed", color=lightsalmon, fontsize=12]',
        'unknown' : '[shape=box, style=dotted, color=red, fontsize=12]',
        'unknown-init' : '[shape=box, style=dotted, color=red, fontsize=12]',
        'unknown-unused' : '[shape=box, style=dotted, color=red, fontsize=12]',
        'unknown-init-unused' : '[shape=box, style=dotted, color=red, fontsize=12]'
    }
    
    EDGE_STYLES = {
        'diff' : '[style=solid, arrowhead=empty, color=royalblue4]',
        'diff-unused' : '[style=dashed, arrowhead=empty, color=royalblue4]',
        'alg' : '[style=solid, arrowhead=empty, color=darkorchid4]',
        'alg-unused' : '[style=dashed, arrowhead=empty, color=darkorchid4]',
        'assign' : '[style=solid, arrowhead=empty, color=deeppink4]',
        'assign-unused' : '[style=dashed, arrowhead=empty, color=deeppink4]',
        'assign-init' : '[style=solid, arrowhead=empty, color=salmon]',
        'assign-init-unused' : '[style=dashed, arrowhead=empty, color=salmon]'
    }      
    
    gv = '/* GraphViz depiction of the model dependency structure for %s */\n\n' % config['name']
    
    # it is possible in some situations to have a model name that isn't a valid identifier
    # so strip out inappropriate chars here
    gv += 'digraph %s_Dependencies {\n' % re.sub('[^0-9a-zA-Z]+', '_', config['name'])
    
    if config.get('graph-horizontal', False):
        gv += 'rankdir="LR";\n'
    
    interms = model['intermeds'] + model['extern']
    if config['input-makes-intermed']:
        # check for reclassified params
        interms += [name for name in graph['nodes'] if graph['nodes'][name]['class']=='intermed' and name not in interms]
    
    if config['graph-exclude-params']:
        nodeorder = interms + model['algs'] + model['diffs']
    else:
        nodeorder = model['params'] + interms + model['algs'] + model['diffs']
    
    nodeorder = model['inputs'] + [x for x in nodeorder if x not in model['inputs']]
    
    drawn = []
    
    for name in nodeorder:
        exclude = False
        node = graph['nodes'][name]
        style = node['class']
        if node['init']:
            if not config['graph-exclude-init']:
                style += '-init'
            else:
                exclude = True
        if node['unused']:
            if not config['graph-exclude-unused']:
                style += '-unused'
            else:
                exclude = True
        if node['init-unused'] and config['graph-exclude-unused'] and config['graph-exclude-init']:
            exclude = True
        
        if not exclude:
            gv += '%s %s;\n' % (name, NODE_STYLES[style])
            drawn.append(name)
    
    # set a default node style for any nodes that we haven't already created
    # but that get referred to by an edge
    gv += 'node %s;\n' % NODE_STYLES['unknown']
    
    if not config['graph-exclude-clusters']:
        for clust in graph['clusters']:
            gv += 'subgraph %s {\n' % clust
            gv += 'style="rounded,bold,filled";\n'
            gv += 'fillcolor=honeydew;\n'
            gv += 'color=darkseagreen;\n'
            for name in graph['clusters'][clust]:
                if name in drawn:
                    gv += '%s;\n' % name
            gv += '}\n'
    
    for key in graph['edges']:
        edge = graph['edges'][key]
        # TODO: possibly rationalise this somewhat -- eg, by just excluding everything with an end not in drawn?
        #exclude = config['graph-exclude-params'] and ((edge['from'] in model['params'] and edge['from'] not in model['inputs'])
        #                                               or (edge['to'] in model['params'] and edge['to'] not in model['inputs']))
        exclude = edge['from'] not in drawn or edge['to'] not in drawn
        style = edge['class']
        if edge['init']:
            if not config['graph-exclude-init']:
                style += '-init'
            else:
                exclude = True
        if edge['unused']:
            if not config['graph-exclude-unused']:
                style += '-unused'
            else:
                exclude = True
        if config['graph-exclude-self'] and edge['from']==edge['to']:
            exclude = True
            
        if edge['init-unused'] and config['graph-exclude-unused'] and config['graph-exclude-init']:
            exclude = True
        
        if not exclude:
            gv += '%s %s;\n' % (key, EDGE_STYLES[style])
    
    gv += '\noverlap=false\n'
    gv += 'label="Dependency Graph for model %s"\n' % config['name']
    gv += '}\n'
    
    return gv


# classify the model dependencies as attributed graph elements
def classify(model, config):
    nodes = {}
    edges = {}
    clusters = {}
    
    for name in model['inputs']:
        nodes[name] = {'name':name, 'class':'input', 'unused':False, 'in':[], 'out':[]}
    
    for name in model['diffs']:
        nodes[name] = {'name':name, 'class':'diff', 'unused':False, 'in':[], 'out':[]}
    
    for name in model['algs']:
        nodes[name] = {'name':name, 'class':'alg', 'unused':False, 'in':[], 'out':[]}
    
    for name in model['intermeds']:
        if name not in nodes:
            nodes[name] = {'name':name, 'class':'intermed', 'in':[], 'out':[],
                           'unused':name in model['unused']}
    
    for name in model['extern']:
        if name not in nodes:
            nodes[name] = {'name':name, 'class':'extern', 'in':[], 'out':[],
                           'unused':name in model['unused']}
    
    for name in model['params']:
        if name not in nodes:
            if config['input-makes-intermed'] and any([ x in model['inputs'] for x in model['symbols'][name]['depends']]):
                nodes[name] = {'name':name, 'class':'intermed', 'in':[], 'out':[], 'unused':False}
            else:
                nodes[name] = {'name':name, 'class':'param', 'in':[], 'out':[],
                               'unused':name in model['unused']}
    
    for name in model['symbols']:
        if name not in nodes:
            nodes[name] = {'name':name, 'class':'unknown', 'in':[], 'out':[],
                           'unused':name in model['unused']}
        
        if model['symbols'][name]['tags']:
            clust = 'cluster_' + model['symbols'][name]['tags'][0]
            if clust in clusters:
                clusters[clust].append(name)
            else:
                clusters[clust] = [name]
        
        for diff in model['symbols'][name]['diffs']:
            for dep in diff['depends']:
                key = '%s -> %s' % (dep, name)
                edges[key] = {'key':key, 'class':'diff',
                              'from':dep, 'to':name,
                              'unused':False, 'init':False}
                nodes[name]['in'].append(edges[key])
                nodes[dep]['out'].append(edges[key])

        for alg in model['symbols'][name]['algs']:
            for dep in alg['depends']:
                key = '%s -> %s' % (dep, name)
                edges[key] = {'key':key, 'class':'alg',
                              'from':dep, 'to':name,
                              'unused':False, 'init':False}
                nodes[name]['in'].append(edges[key])
                nodes[dep]['out'].append(edges[key])
                
        for assign in model['symbols'][name]['assigns']:
            for dep in assign['depends']:
                key = '%s -> %s' % (dep, name)
                if key in edges:
                    edge = edges[key]
                    edge['init'] = edge['init'] and assign['init']
                else:
                    edges[key] = {'key':key, 'class':'assign',
                                  'from':dep, 'to':name,
                                  'unused': (name in model['unused'] or dep in model['unused']),
                                  'init': assign['init'] and nodes[name]['class']=='param'}
                nodes[name]['in'].append(edges[key])
                nodes[dep]['out'].append(edges[key])
                
    for name in nodes:
        nodes[name]['init'] = ( name not in model['inputs']
                                and nodes[name]['class']=='param'
                                and len(nodes[name]['out']) > 0
                                and all([x['init'] for x in nodes[name]['out']]) )
        nodes[name]['init-unused'] = ( name not in model['inputs']
                                       and name not in model['roots']
                                       and name not in model['required']
                                       and all([(x['init'] or x['unused']) for x in nodes[name]['out']]) )
    
    for key in edges:
        edges[key]['init-unused'] = nodes[edges[key]['from']]['init-unused'] or nodes[edges[key]['to']]['init-unused']
    
    return { 'nodes':nodes, 'edges':edges, 'clusters':clusters }

# wrapper application to invoke the above

def process_args():
    config = CONFIG

    ap = argparse.ArgumentParser(description="Get info about a BCMD model.")
    ap.add_argument('-d', help='specify output directory (default: .)', metavar='DIR')
    ap.add_argument('-t', '--text', help='specify output of plain text documentation', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-l', '--latex', help='specify output of LaTeX documentation', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-H', '--html', help='specify output of HTML documentation', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-a', help='generate all major graph variants (using default names)', action='store_true')
    ap.add_argument('-n', '--name', help='specify a model name instead of deriving from file', metavar='NAME')
    ap.add_argument('-U', '--graphxunused', help='specify output of graph excluding unused elements', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-N', '--graphxinit', help='specify output of graph excluding init elements', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-P', '--graphxparam', help='specify output of graph excluding parameters', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-X', '--graphcore', help='specify output of graph excluding both init and unused elements', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-C', '--graphxclust', help='specify output of graph excluding clustering', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-F', '--graphfull', help='specify output of full graph', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-R', '--graphself', help='include direct circular dependencies in graphs', action='store_true')
    ap.add_argument('-s', '--summary', help='print summary info to STDOUT', action='store_true')
    ap.add_argument('-x', '--nograph', help='suppress all graph output', action='store_true')
    ap.add_argument('-v', '--verbose', help='set output verbosity (0-7, default: 5)', metavar='LEVEL', type=int)
    # ... add further options here as needed ...
    
    ap.add_argument('file', help='compiled model info (.bcmpl) file')
    
    args = ap.parse_args()
    
    config['log-info'] = args.summary
    config['no-graph'] = args.nograph
    
    config['filename'] = args.file
    
    if args.name is None:
        config['name'] = os.path.splitext(os.path.split(args.file)[1])[0]
    else:
        config['name'] = args.name
    
    if args.text is not None:
        if args.text == '':
            config['text'] = config['name'] + '.txt'
        else:
            config['text'] = args.text

    if args.latex is not None:
        if args.latex == '':
            config['latex'] = config['name'] + '.tex'
        else:
            config['latex'] = args.latex

    if args.html is not None:
        if args.html == '':
            config['html'] = config['name'] + '.html'
        else:
            config['html'] = args.text
    
    config['graph-exclude-self'] = not args.graphself
    
    # this is ridiculously laboured, but anyway...
    if args.a:
        config['xinit'] = config['name'] + '_no_init.gv'
        config['xunused'] = config['name'] + '_no_unused.gv'
        config['xinitunused'] = config['name'] + '_core_only.gv'
        config['xclust'] = config['name'] + '_no_clusters.gv'
        config['full'] = config['name'] + '.gv'
        config['xparam'] = config['name'] + '_no_params.gv'
    else:
        if args.graphxunused is not None:
            if args.graphxunused == '':
                config['xunused'] = config['name'] + '_no_unused.gv'
            else:
                config['xunused'] = args.graphxunused
                
        if args.graphxinit is not None:
            if args.graphxinit == '':
                config['xinit'] = config['name'] + '_no_init.gv'
            else:
                config['xinit'] = args.graphxinit

        if args.graphcore is not None:
            if args.graphcore == '':
                config['xinitunused'] = config['name'] + '_core_only.gv'
            else:
                config['xinitunused'] = args.graphcore
            
        if args.graphxclust is not None:
            if args.graphxclust == '':
                config['xclust'] = config['name'] + '_no_clusters.gv'
            else:
                config['xclust'] = args.graphxclust

        if args.graphfull is not None:
            if args.graphfull == '':
                config['full'] = config['name'] + '.gv'
            else:
                config['full'] = args.graphfull

        if args.graphxparam is not None:
            if args.graphxparam == '':
                config['xparam'] = config['name'] + '_no_params.gv'
            else:
                config['xparam'] = args.graphxparam
                
    if args.d is not None:
        config['outdir'] = args.d
    
    if args.verbose is None:
        logger.verbosity = logger.MESSAGE
    else:
        logger.verbosity = args.verbose  
    
    return config


def load_model(config):
    with open(config['filename']) as f:
        return eval(f.read())

def make_graphs(model, config):
    # default setting is 'full'
    if 'full' in config:
        with open(os.path.join(config['outdir'], config['full']), 'w') as f:
            print >> f, generateGraphViz(model, config)

    # other versions we will set as we go
    if 'xinit' in config:
        config['graph-exclude-init'] = True
        with open(os.path.join(config['outdir'], config['xinit']), 'w') as f:
            print >> f, generateGraphViz(model, config)
    
    if 'xunused' in config:
        config['graph-exclude-init'] = False
        config['graph-exclude-unused'] = True
        with open(os.path.join(config['outdir'], config['xunused']), 'w') as f:
            print >> f, generateGraphViz(model, config)
    
    if 'xinitunused' in config:
        config['graph-exclude-init'] = True
        config['graph-exclude-unused'] = True
        with open(os.path.join(config['outdir'], config['xinitunused']), 'w') as f:
            print >> f, generateGraphViz(model, config)
        
    # somewhat awkwardly, we leave any init and unused exclusions in place
    # for the clusterless and/or paramless versions, so that variants can be generated if required
    # without yet more config arsing about...
    if 'xparam' in config:
        config['graph-exclude-params'] = True
        with open(os.path.join(config['outdir'], config['xparam']), 'w') as f:
            print >> f, generateGraphViz(model, config)
    
    if 'xclust' in config:
        config['graph-exclude-clusters'] = True
        with open(os.path.join(config['outdir'], config['xclust']), 'w') as f:
            print >> f, generateGraphViz(model, config)


if __name__ == '__main__':
    config = process_args()
    if not config: sys.exit(2)
    
    model = load_model(config)
    if model:
        if not config['no-graph']:
            make_graphs(model, config)
        if config['text']:
            doc_text.writeDoc(model, config)
        if config['latex']:
            doc_latex.writeDoc(model, config)
        if config['html']:
            doc_html.writeDoc(model, config)
        if config['log-info']:
            logger.dest = sys.stdout
            logModelInfo(model, config)

