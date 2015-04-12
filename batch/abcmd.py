#! /usr/bin/env python
# functions to invoke a single-model abcsmc run

import numpy, numpy.ma
import os, os.path, sys
import time, datetime
import argparse, pprint

# local hacked down version of abc-sysbio
import abcsbh.data
import abcsbh.abcsmc
import abcsbh.input_output

# local BCMD-related modules
import model_bcmd
import steps
import distance
import inputs

# environment
VERSION = 0.2
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.relpath('../build', HERE))
WORK = BUILD

# defaults
NPARTICLES=500
NBATCH=1
BETA=1
MODELKERNEL=0.7
FINALEPSILON=1.5
ALPHA=0.75

PARAM_SELECT = '*'
DISTANCE = 'euclidean'

CONFIG = { 'distance': DISTANCE,
           'build' : BUILD,
           'work' : None,
           'nbatch' : NBATCH,
           'beta' : BETA,
           'param_select': PARAM_SELECT,
           'job' : None,
           'data' : None }

# process command-line arguments
def process_args():
    ap = argparse.ArgumentParser(description="Approximate Bayesian parameter estimation for BCMD models")
    ap.add_argument('--version', action='version', version='abcmd version %.1fa' % VERSION)
    ap.add_argument('jobfile', help='job specification file')
    ap.add_argument('datafile', help='CSV containing time series data')
    
    args = ap.parse_args()

    return args.jobfile, args.datafile


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
def process_inputs(jobfile, datafile):
    config = CONFIG
    
    job = inputs.readFile(jobfile)
    data = inputs.readFile(datafile)
    
    timedata = data['timeseries']
    
    # check for required inputs
    for field in ['model', 'var', 'input']:
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
                    if ',' in line:
                        pp = [x.strip() for x in line.split(',')]
                    else:
                        pp = line.split()
                        
                    try:
                        dummy = float(pp[2])
                        params.append(pp)
                    except (ValueError, IndexError):
                        pass

    ins = job['header']['input']

    # list of chosen params, or '*' for all known
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
    
    config['work'] = workdir
    
    # TODO: allow more levels of control over this stuff in the job file
    config['name'] = model
    config['program'] = job['header'].get('program', [[os.path.join(BUILD, model + '.model')]])[0][0]
    config['model_io'] = job['header'].get('model_io', [[os.path.join(workdir, 'model_io')]])[0][0]
    config['abc_io'] = job['header'].get('abc_io', [[os.path.join(workdir, 'abc_io')]])[0][0]

    if not os.path.isfile(config['program']):
        raise Exception("model executable '%s' does not exist" % config['program'])
        
    if tname not in timedata:
        raise Exception("time step field '%s' not present in data file" % tname)
    
    config['times'] = timedata[tname]
    config['vars'] = process_vars(vars, aliases, timedata)
    config['params'] = process_vars(params, aliases, timedata)
    
    if param_select != PARAM_SELECT:
        all_params = config['params']
        config['params'] = []
        for param in all_params:
            if param['name'] in param_select:
                config['params'].append(param)
    
    config['inputs'] = process_vars(ins, aliases, timedata)
    
    config['baseSeq'], dummy = steps.readFiles(job['header'].get('init', [[]])[0])
    config['particles'] = int(job['header'].get('particles', [[NPARTICLES]])[0][0])
    config['nbatch'] = int(job['header'].get('nbatch', [[NBATCH]])[0][0])
    config['modelKernel'] = float(job['header'].get('modelKernel', [[MODELKERNEL]])[0][0])
    config['finalepsilon'] = float(job['header'].get('finalepsilon', [[FINALEPSILON]])[0][0])
    config['alpha'] = float(job['header'].get('alpha', [[ALPHA]])[0][0])    
    config['beta'] = int(job['header'].get('beta', [[BETA]])[0][0])

    config['timeout'] = int(job['header'].get('timeout', [[model_bcmd.TIMEOUT]])[0][0])
    
    # ABC-SYSBIO distance funcs have the same names as ordinary ones but with suffix "Distance"
    # TODO: handle loglik sigma factory
    config['distance'] = getattr(distance, job['header'].get('distance', [[DISTANCE]])[0][0] + "Distance")

    return config

# set up elements ready to simulate
# by this point any and all file parsing has taken place and default provided
# -- we try not to enmesh this with a particular input structure, because duh
def setupABC ( modelname,
               program,
               times,                # list of float
               vars,                 # structure as above
               params,               # ditto
               inputs,               # ditto
               workdir,
               deleteWorkdir,
               pickling,
               abcIOname,
               baseSeq = [],
               particles=NPARTICLES,
               nbatch=NBATCH,
               beta=BETA,
               modelKernel=MODELKERNEL,
               distance=DISTANCE,
               timeout=model_bcmd.TIMEOUT ):
    
    model = model_bcmd.model_bcmd( name=modelname, vars=vars, params=params,
                                   inputs=inputs, times=times,
                                   program=program, baseSeq=baseSeq,
                                   workdir=workdir, deleteWorkdir=deleteWorkdir,
                                   timeout=timeout )
    
    # it is not clear that we actually need a masked array, but...
    masked = numpy.transpose(numpy.ma.array( [ x['points'] for x in vars ] ))
    data = abcsbh.data.data( times, masked )
    
    io = abcsbh.input_output.input_output( abcIOname )
    io.create_output_folders([modelname], particles, pickling )
    
    algorithm = abcsbh.abcsmc.abcsmc( models = [model],
                                      nparticles = particles,
                                      modelprior = [1],
                                      data = data,
                                      beta = beta,
                                      nbatch = nbatch,
                                      modelKernel = modelKernel,
                                      debug = False,
                                      timing = False,
                                      distancefn = distance )
    
    return algorithm, io

# run an already-configured simulation
# -- this doesn't really merit its own function, but we don't
# yet have any other context for it...
def runABC ( algorithm, io, finalEpsilon, alpha ):
    algorithm.run_automated_schedule(finalEpsilon, alpha, io)


# main entry point
# provide a job file and a data file
if __name__ == '__main__':
    job, data = process_args()
    config = process_inputs(job, data)
    algo, io = setupABC( config['name'], config['program'], config['times'],
                         config['vars'], config['params'], config['inputs'],
                         config['model_io'], False, True, config['abc_io'],
                         config['baseSeq'], config['particles'], config['nbatch'],
                         config['beta'], config['modelKernel'], config['distance'],
                         config['timeout'] )
    runABC( algo, io, [config['finalepsilon']], config['alpha'] )
