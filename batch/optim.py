#! /usr/bin/env python
# optimise parameters for a BCMD model to resemble a known output

import numpy as np
import numpy.random as npr
import scipy.stats as stats
import os, os.path, sys
import time, datetime
import argparse, pprint

# optimisation
import openopt

# local BCMD-related modules
import model_bcmd
import steps
import distance
import inputs

# add location of pswarm_py.so to search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib')))

# environment
VERSION = 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.relpath('../build', HERE))
INFO = 'optim.info'

# defaults
JOB_MODE = 'GLP'
SOLVER = 'pswarm'
PARAM_SELECT = '*'
DISTANCE = 'euclidean'
MAX_ITER = 1e3
STEADY = 1000

CONFIG = { 'build': BUILD,
           'work': None,
           'info': INFO,
           'job_mode': JOB_MODE,   # it probably doesn't make sense for this to be anything other than GLP, but...
           'solver': SOLVER,
           'nbatch': 1,            # we don't support parallel execution at present
           'beta': 1,              # ditto
           'param_select': PARAM_SELECT,
           'weights': {},
           'timestep': None }     

# process command-line arguments
def process_args():
    ap = argparse.ArgumentParser(description="Parameter optimisation for BCMD models")
    ap.add_argument('--version', action='version', version='optim version %.1fa' % VERSION)
    ap.add_argument('-b', '--build', help='build/model directory (default: [BCMD_HOME]/build)', metavar='DIR')
    ap.add_argument('-o', '--outdir', help='work/output directory (default: [BUILD]/[MODEL_NAME]/[TIMESTAMP]', metavar='DIR')
    ap.add_argument('-d', '--dryrun', help='dump configuration details without simulating', action='store_true')
    ap.add_argument('-w', '--wetrun', help='single test run and data dump without full optimisation', action='store_true')
    ap.add_argument('-D', '--debug', help='run in debug mode, logging various things to stderr', action='store_true')
    ap.add_argument('jobfile', help='job specification file')
    ap.add_argument('datafile', help='CSV containing time series data')
    
    args = ap.parse_args()

    config = CONFIG
    config['jobfile'] = args.jobfile
    config['datafile'] = args.datafile
        
    if args.build:
        config['build'] = args.build
    else:
        config['build'] = BUILD
    
    if args.outdir:
        config['work'] = args.outdir
    # otherwise leave as None and concoct after reading job file

    config['dryrun'] = args.dryrun
    config['wetrun'] = args.wetrun
    config['debug'] = args.debug
    
    return config

# convert a vars or params list into the required dictionary format,
# pulling points from the data file, with alias redirection as necessary
def process_vars(vars, aliases, data):
    result = []
    names = []
    for item in vars:
        name = item[0]
        
        if name in names:
            continue
        else:
            names.append(name)
        
        var = { 'name': name }
        
        if name in aliases:
            dataname = aliases[name]
        else:
            dataname = name
        
        if dataname in data:
            var['points'] = data[dataname]
        
        if len(item) > 1:
            var['dist'] = item[1]
            
            if item[1] == 'constant' and len(item) > 2:
                var['value'] = float(item[2])
                if len(item) > 4:
                    var['default'] = float(item[4])
                else:
                    var['default'] = var['value']
            elif (item[1] == 'normal' or item[1] == 'lognormal') and len(item) > 2:
                var['mean'] = float(item[2])
                if len(item) > 3:
                    var['var'] = float(item[3])
                if len(item) > 4:
                    var['default'] = float(item[4])
                elif var['dist'] == 'lognormal':
                    var['default'] = numpy.exp(var['mean'])
                else:
                    var['default'] = var['mean']
            elif item[1] == 'uniform' and len(item) > 2:
                var['min'] = float(item[2])
                if len(item) > 3:
                    var['max'] = float(item[3])
                if len(item) > 4:
                    var['default'] = float(item[4])
                else:
                    var['default'] = (var['min'] + var['max']) / 2
                
        result.append(var)
    
    return result

# get job details from input files
def process_inputs(config):

    job = inputs.readFile(config['jobfile'])
    data = inputs.readFile(config['datafile'])
    
    # there's scope for something silly to go wrong here, but for now
    # let's just assume it won't...
    timedata = data['timeseries']
    
    # check for required inputs -- typically param and/or input may also be needed,
    # but it is conceivable that one might want to run a job without them
    for field in ['model', 'var']:
        if field not in job['header']:
            raise Exception("field '%s' must be specified in the job file" % field)
    
    model = job['header']['model'][0][0]
    vars = job['header']['var']
    params = job['header'].get('param', [])
    
    # params specified in external files are added after, and skipped by
    # process_vars if already specified by a param line
    param_file = job['header'].get('param_file', [])
    for item in param_file:
        for filename in item:
            with open(filename) as f:
                for line in f:
                    pp = [x.strip() for x in line.split(',')]
                    try:
                        dummy = float(pp[2])
                        params.append(pp)
                    except ValueError:
                        pass
        
    ins = job['header'].get('input', [])
    
    # list of chosen params, or '*' for all known (but really, don't do that!)
    param_select = job['header'].get('param_select', [[PARAM_SELECT]])
    param_select = [x for line in param_select for x in line]
    if PARAM_SELECT in param_select: param_select = PARAM_SELECT
    
    aliaslist = job['header'].get('alias', [])
    aliases = {}
    for alias in aliaslist:
        aliases[alias[0]] = alias[1]
    
    tname = aliases.get('t', inputs.LOCAL_TIME)
    
    if config['work']:
        workdir = os.path.join(config['build'], config['work'])
    else:
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S')
        workdir = os.path.join(config['build'], model, timestamp)
    
    config['name'] = model
    config['program'] = job['header'].get('program', [[os.path.join(BUILD, model + '.model')]])[0][0]
    config['model_io'] = job['header'].get('model_io', [[os.path.join(workdir, 'model_io')]])[0][0]
    config['work'] = workdir
    config['info'] = os.path.join(workdir, config['info'])
    
    if 'timestep' in job['header']:
        config['timestep'] = float(job['header']['timestep'][0][0])
    
    if tname not in timedata:
        if config['timestep']:
            stepcount = len(timedata[timedata.keys()[0]])
            timedata[tname] = np.array(range(stepcount)) * config['timestep']
        else:
            raise Exception("time step field '%s' not present in data file" % tname)
    
    config['times'] = timedata[tname]
    config['vars'] = process_vars(vars, aliases, timedata)
    config['params'] = process_vars(params, aliases, timedata)
    config['param_unselect'] = []
    
    if param_select != PARAM_SELECT:
        all_params = config['params']
        config['params'] = []
        for param in all_params:
            if param['name'] in param_select:
                config['params'].append(param)
            else:
                config['param_unselect'].append(param)
    
    config['inputs'] = process_vars(ins, aliases, timedata)
    
    config['baseSeq'], dummy = steps.readFiles(job['header'].get('init', [[]])[0])
    
    config['job_mode'] = job['header'].get('job_mode', [[JOB_MODE]])[0][0]
    config['solver'] = job['header'].get('solver', [[SOLVER]])[0][0]
    
    config['steady'] = float(job['header'].get('steady', [[STEADY]])[0][0])
    config['max_iter'] = int(job['header'].get('max_iter', [[MAX_ITER]])[0][0])
    
    weights = job['header'].get('weight', {})
    for weight in weights:
        config['weights'][weight[0]] = float(weight[1])
    
    # for the moment the only supported distance functions are in the distance module
    # if that's ever not the case this could be a bit trickier...
    config['distance'] = getattr(distance, job['header'].get('distance', [[DISTANCE]])[0][0])

    return config

# build model
def make_model(config):
    if config['dryrun']:
        return None
    
    model = model_bcmd.model_bcmd( name=config['name'],
                                   vars=config['vars'],
                                   params=config['params'],
                                   inputs=config['inputs'],
                                   times=config['times'],
                                   program=config['program'],
                                   fixed=config['param_unselect'],
                                   baseSeq=config['baseSeq'],
                                   workdir=config['model_io'],
                                   deleteWorkdir=False,
                                   debug=config['debug'],
                                   steady=config['steady'])
    return model

# create optimiser -- only GLP supported so far
def make_optimiser(config, model):
    if not model: return None
    
    # run with dummy values -- this doesn't really belong here, but temporarily...
    if config['wetrun']:
        print "--\nGenerating optimisable function"
        ff = model.optimisable(config['distance'], debug=config['debug'])
        print ff
        print "--\nAttempting single run of function"
        pp = [ x.get('default', 0) for x in config['params'] ]
        ff(pp)
        return None

    mode = config.get('job_mode', JOB_MODE)
    weights = [ config['weights'].get(x['name'], 1) for x in config['vars'] ]
    if mode == 'GLP':
        lb = [ x.get('min', 0) for x in config['params'] ]
        ub = [ x.get('max', 0) for x in config['params'] ]
        return openopt.GLP( model.optimisable(config['distance'], weights=weights),
                            lb = lb,
                            ub = ub,
                            # TODO, possibly: support A and b args to define linear constraints
                            maxIter = config['max_iter'] )
    elif mode == 'NLP':
        lb = [ x.get('min', 0) for x in config['params'] ]
        ub = [ x.get('max', 0) for x in config['params'] ]
        return openopt.NLP( model.optimisable(config['distance'], weights=weights),
                            lb = lb,
                            ub = ub,
                            # TODO, possibly: support A and b args to define linear constraints
                            maxIter = config['max_iter'] )
    elif mode == 'NSP':
        lb = [ x.get('min', 0) for x in config['params'] ]
        ub = [ x.get('max', 0) for x in config['params'] ]
        return openopt.NSP( model.optimisable(config['distance'], weights=weights),
                            lb = lb,
                            ub = ub,
                            # TODO, possibly: support A and b args to define linear constraints
                            maxIter = config['max_iter'] )
    return None

# run optimiser
# choice of solver comes from config, we just assume it's compatible with
# the problem structure -- if not this will fail (duh)
def optimise(config, model, optimiser):
    x0 = [ x.get('default', 0) for x in config['params'] ]
    return optimiser.solve( config['solver'], x0=x0, plot=0, debug=0 )

# main entry point
# provide a job file and a data file
if __name__ == '__main__':
    config = process_args()
    if config:
        process_inputs(config)
        model = make_model(config)
        optimiser = make_optimiser(config, model)
        
        if optimiser:
        
            rr = optimise(config, model, optimiser)
            
            # for the moment we just print the results here
            # -- which may be superfluous, since OO will print stuff as well
            
            print "\nRESULTS\n"
            print "Stop case %g: %s" % (rr.istop, rr.msg)
            if rr.isFeasible: print "Feasible solution found"
            else: print "No feasible solution found"
            print "Final distance value: %f" % rr.ff
            print "Final parameter values:"
            for ii in range(len(rr.xf)):
                print "  %s: %f" % (config['params'][ii]['name'], rr.xf[ii])
        
        else:
            print 'CONFIG:'
            pprint.pprint(config)
