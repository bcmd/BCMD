#!/usr/bin/python
#
# CLI compiler for bcmd's new model description language
#

import sys
import argparse
import bcmd_yacc
import os
import decimal
import string
import pprint
import logger
import ast
import codegen
import info

# default compiler configuration
# (this is effectively a template whose details
# may be adapted by command line args)
CONFIG = { 'modelpath': ['.', 'models' ],
           'outdir' : '.',
           'outfile' : None,
           'treefile' : None,
           'name' : None,
           'unused' : True,
           'graph' : None,
           'graph-exclude-unused': False,
           'graph-exclude-init': False,
           'graph-exclude-self': True,
           'graph-exclude-clusters': False,
           'graph-exclude-params':False,
           'independent' : 't',
           'input-makes-intermed':True }

# these are effectively constants
VERSION = 0.5
MODELDEF_EXT = '.modeldef'
CODE_EXT = '.c'
MODEL_EXT = '.model'
TREE_EXT = '.tree'
COMPILE_EXT = '.bcmpl'
GRAPHVIZ_EXT = '.gv'

DUMMY_SOURCE = '##\n'

# parse a chosen model definition file and return the AST
def parse_file ( filename ):
    try:
        f = open(filename)
        data = f.read()
        f.close()
    except IOError as e:
        logger.error("I/O error({0}): {1}".format(e.errno, e.strerror))
        return None
    
    logger.message("Processing file: " + filename)
    
    bcmd_yacc.currentFile = filename
    errsBefore = len(bcmd_yacc.compilationInfo['errors'])

    lp = bcmd_yacc.get_lexer_parser()
    result = lp[1].parse(data, lexer=lp[0])
    
    fileErrs = len(bcmd_yacc.compilationInfo['errors']) - errsBefore
    bcmd_yacc.currentFile = None
    
    if fileErrs == 1:
        logger.error('Compilation failed with 1 syntax error')
    elif fileErrs > 1:
        logger.error('Compilation failed with %d syntax errors' % fileErrs)
        
    return fileErrs, result

def print_errors():
    logger.error('*** Summary of model compilation errors ***')
    errs = bcmd_yacc.compilationInfo
    for ii in range(len(errs['errors'])):
        logger.error(errs['messages'][ii]
                     + ' (' + errs['files'][ii]
                     + ', line ' + str(errs['lines'][ii]) +')' )

# find a file on the search path
def search_file(filename, search_path):
    for path in search_path:
        candidate = os.path.join(path, filename)
        if os.path.exists(candidate): return os.path.abspath(candidate)
    return None

# process arguments
def process_args():
    config = CONFIG

    ap = argparse.ArgumentParser(description="Model compiler for the BCMD modelling system.")
    ap.add_argument('--version', action='version', version='bcmd version %.1fa' % VERSION)
    ap.add_argument('-i', help='append to default model search path', metavar='PATH')
    ap.add_argument('-I', help='replace default model search path', metavar='PATH')
    ap.add_argument('-n', '--name', help='specify model name (default: <file1>)', metavar='NAME')
    ap.add_argument('-o', help='specify output file name (default: <modelname>.model)', metavar='FILE')
    ap.add_argument('-d', help='specify output directory (default: .)', metavar='DIR')
    ap.add_argument('-u', '--unused', help='omit apparently unused intermediates', action='store_false')
    ap.add_argument('-g', '--debug', help='include debug outputs in generated model code', action='store_true')
    ap.add_argument('-t', '--tree', help='write parse tree to file (default: <modelname>.tree)', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-p', '--processed', help='write compilation data to file (default: <modelname>.bcmpl)', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-G', '--graph', help='write dependency structure in GraphViz format (default: <modelname>.gv)', nargs='?', default=None, const='', metavar='FILE')
    ap.add_argument('-U', '--graphxunused', help='exclude apparently unused elements from graph output', action='store_true')
    ap.add_argument('-N', '--graphxinit', help='exclude initialisation dependencies from graph output', action='store_true')
    ap.add_argument('-C', '--graphxclust', help='exclude clustering from graph output', action='store_true')
    ap.add_argument('-S', '--graphself', help='include direct circular dependencies in graph output', action='store_false')
    ap.add_argument('-v', '--verbose', help='set level of detail logged to stderr (0-7, default: 3)', metavar='LEVEL', type=int)
    ap.add_argument('-Y', '--yacc', help='run a dummy parse to rebuild parse tables', action='store_true')
    # ... add further options here as needed ...
    
    ap.add_argument('file', nargs='+', help='one or more model description files to be compiled')
    
    args = ap.parse_args()
    
    if args.yacc:
        lp = bcmd_yacc.get_lexer_parser()
        result = lp[1].parse(DUMMY_SOURCE, lexer=lp[0])
        return False
    
    if not (args.I is None):
        config['modelpath'] = string.split(args.I, os.pathsep)
    elif not (args.i is None):
        config['modelpath'] = config['modelpath'] + string.split(args.i, os.pathsep)
    
    if not (args.name is None): config['name'] = args.name
    else:
        srcname, srcext = os.path.splitext(args.file[0])
        config['name'] = srcname
    
    if not (args.o is None): config['outfile'] = args.o
    else:
        config['outfile'] = config['name'] + MODEL_EXT
    
    if args.d is not None:
        if not os.path.isdir(args.d): os.makedirs(args.d)
        config['outdir'] = args.d
    
    config['treefile'] = args.tree
    config['compfile'] = args.processed
    config['sources'] = args.file
    config['unused'] = args.unused
    config['debug'] = args.debug
    config['graph'] = args.graph
    config['graph-exclude-unused'] = args.graphxunused
    config['graph-exclude-init'] = args.graphxinit
    config['graph-exclude-self'] = args.graphself
    config['graph-exclude-clusters'] = args.graphxclust
    
    if args.verbose is not None:
        logger.verbosity = args.verbose
    return config

# load and parse source files named on the command line, plus imports
# note failures and return a structure including those details and
# the resulting merged item list
def load_sources(config):
    sources = config['sources']
    srcIndex = 0
    parsedSources = []
    failedSources = []
    merged = []
    
    while srcIndex < len(sources):
        logger.message("Searching for source file: " + sources[srcIndex])
        src = search_file(sources[srcIndex], config['modelpath'])
        if ( src is None ) and ( not sources[srcIndex].endswith(MODELDEF_EXT) ):
            logger.message("Not found, trying with added extension: " + sources[srcIndex] + MODELDEF_EXT)
            src = search_file(sources[srcIndex] + MODELDEF_EXT, config['modelpath'])
        
        if src is None:
            logger.warn("File not found: " + sources[srcIndex])
            failedSources.append[sources[srcIndex]]
        else:
            nErrs, ast = parse_file(src)
            if nErrs > 0 or ast is None:
                failedSources.append(src)
            else:
                ast = list(ast)
            
                # add imports that are not already in the source list to it
                for imp in list(sum([x[1:] for x in ast if x[0]=='import'], ())):
                    if imp not in sources and imp + MODELDEF_EXT not in sources:
                        sources.append(imp)
            
                logger.detail(ast, prettify=True)
            	parsedSources.append((sources[srcIndex],src))
            
                merged = merged + ast
        
        srcIndex = srcIndex + 1
    
    logger.message("Total number of attempted source files: %d" % srcIndex)
    logger.message("%d parsed, %d failed" % (len(parsedSources), len(failedSources)))
    
    return {'sources':sources, 'parsed':parsedSources, 'failed':failedSources, 'merged':merged}


# write the loaded merged item list to a file, if so specified
def write_tree(config, work):
    if not config['treefile'] is None:
        if config['treefile'] == '':
            config['treefile'] = config['name'] + TREE_EXT
        treePath = os.path.join(config['outdir'], config['treefile'])
        logger.message("Attempting to write parse tree to " + treePath)
    	try:
    	    treeStream = open(treePath, 'w')
    	    pprint.pprint(work['merged'], stream=treeStream)
    	    treeStream.close()
    	except IOError as e:
    	    logger.error("Error writing file ({0}): {1}".format(e.errno, e.strerror))

# write the processed model structure to a file, if so specified
def write_comp(config, processed):
    if not config['compfile'] is None:
        if config['compfile'] == '':
            config['compfile'] = config['name'] + COMPILE_EXT
        compPath = os.path.join(config['outdir'], config['compfile'])
        logger.message("Attempting to write compilation structure to " + compPath)
    	try:
    	    compStream = open(compPath, 'w')
    	    pprint.pprint(processed, stream=compStream)
    	    compStream.close()
    	except IOError as e:
    	    logger.error("Error writing file ({0}): {1}".format(e.errno, e.strerror))

# write the model dependencies to a graph, if so specified
def write_graph(config, model):
    if not config['graph'] is None:
        if config['graph'] == '':
            config['graph'] = config['name'] + GRAPHVIZ_EXT
        graphPath = os.path.join(config['outdir'], config['graph'])
        logger.message("Attempting to write dependency graph to " + graphPath)
    	try:
    	    stream = open(graphPath, 'w')
    	    print >> stream, info.generateGraphViz(model, config)
    	    stream.close()
    	except IOError as e:
    	    logger.error("Error writing file ({0}): {1}".format(e.errno, e.strerror))

#----------------------------------------------------------------------------

# main entry point of this compiler script
if __name__ == '__main__':
    config = process_args()
    if not config: sys.exit(2)
    
    work = load_sources(config)
    if len(work['failed']) > 0:
        print_errors()
        sys.exit(1)
    
    write_tree(config, work)
    
    processed = ast.process(work['merged'], work['parsed'], config['independent'])
    info.logModelInfo(processed, config)
    write_comp(config, processed)
    write_graph(config, processed)
    
    source = codegen.generateSource(processed, config)
    
    codepath = os.path.join(config['outdir'], config['name'] + CODE_EXT)
    logger.message("Attempting to write C code to " + codepath)
    
    try:
        cfile = open(codepath, 'w')
        cfile.write(source)
        cfile.close()
    except IOError as e:
        logger.error("Error writing file ({0}): {1}".format(e.errno, e.strerror))
        sys.exit(1)

