#! /usr/bin/env python
# run a job involving multiple BCMD model simulations

# there may eventually be multiple kinds supported, and the ABC stuff may be merged
# but to start with this is specifically for deterministic jobs looking at model
# behavioural variation with parameters

import numpy as np
import numpy.random as npr
import scipy.stats as stats
import os, os.path, sys
import time, datetime
import argparse, pprint

# we now delegate sensitivity analysis to an external library
# initially still only supporting Morris, but this will soon change...
# TODO: add support for eFAST, maybe others
import SALib.sample.morris
import SALib.analyze.morris
import SALib.sample.fast_sampler
import SALib.analyze.fast

# local BCMD-related modules
import model_bcmd
import steps
import distance
import inputs
import posthoc

# environment
VERSION = 0.6
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.relpath('../build', HERE))
INFO = 'dsim.info'

# defaults
DIVISIONS = 10
NBATCH = 1
BETA = 1
JOB_MODE = 'single'
PARAM_SELECT = '*'
NPATH = 10
JUMP = 4
INTERFERENCE = 4
SAVE_INTERVAL = 100
DISTANCE = 'euclidean'
DELTA = 1e-6

# suppress stray floating point warnings
np.seterr(all='ignore')

CONFIG = { 'build': BUILD,
           'work': None,
           'info': INFO,
           'divisions': DIVISIONS,
           'nbatch': NBATCH,
           'npath': NPATH,
           'perturbed': False,
           'beta': BETA,
           'param_select': PARAM_SELECT,
           'save_interval': SAVE_INTERVAL,
           'timeout': model_bcmd.TIMEOUT,
           'jump': JUMP,
           'delta': DELTA,
           'relative_delta': True,
           'weights' : {},
           'sigma' : None }

# numpy utility for constructing a cartesian product of arrays
# by StackOverflow user .pv, answering this question:
# http://stackoverflow.com/questions/1208118/
def cartesian(arrays, out=None):
    """
    Generate a cartesian product of input arrays.

    Parameters
    ----------
    arrays : list of array-like
        1-D arrays to form the cartesian product of.
    out : ndarray
        Array to place the cartesian product in.

    Returns
    -------
    out : ndarray
        2-D array of shape (M, len(arrays)) containing cartesian products
        formed of input arrays.

    Examples
    --------
    >>> cartesian(([1, 2, 3], [4, 5], [6, 7]))
    array([[1, 4, 6],
           [1, 4, 7],
           [1, 5, 6],
           [1, 5, 7],
           [2, 4, 6],
           [2, 4, 7],
           [2, 5, 6],
           [2, 5, 7],
           [3, 4, 6],
           [3, 4, 7],
           [3, 5, 6],
           [3, 5, 7]])

    """

    arrays = [np.asarray(x) for x in arrays]
    dtype = arrays[0].dtype

    n = np.prod([x.size for x in arrays])
    if out is None:
        out = np.zeros([n, len(arrays)], dtype=dtype)

    m = n / arrays[0].size
    out[:,0] = np.repeat(arrays[0], m)
    if arrays[1:]:
        cartesian(arrays[1:], out=out[0:m,1:])
        for j in xrange(1, arrays[0].size):
            out[j*m:(j+1)*m,1:] = out[0:m,1:]
    return out

# calculate a range of values to regularly sample a var (or param or input) distribution
# for a uniform distribution we include the endpoints, for
# log/normal we (obviously) don't, instead treating as (n+2) and dropping the ends
# for constants, we return an array of length 1, and length 0 for unrecognised
def quantiles(var, n):
    dist = var.get('dist', '')
    if dist == 'constant':
        return np.array([var.get('value', np.nan)])
    elif dist == 'uniform':
        return np.linspace(var.get('min', 0), var.get('max', 1), n)
    elif dist == 'normal':
        return stats.norm.ppf(np.linspace(0,1,n+2)[range(1,n+1)],
                              loc=var.get('mean', 0),
                              scale=np.sqrt(var.get('var', 1)))
    elif dist == 'normal':
        return stats.lognorm.ppf(np.linspace(0,1,n+2)[range(1,n+1)],
                                 loc=var.get('mean', 0),
                                 scale=np.sqrt(var.get('var', 1)))
    elif dist == 'noinit':
        return np.array([None])
    else:
        return np.array([])

# process command-line arguments
def process_args():
    ap = argparse.ArgumentParser(description="Batch simulation jobs for BCMD models")
    ap.add_argument('--version', action='version', version='dsim version %.1fa' % VERSION)
    ap.add_argument('-r', '--results', help='output file name (default: results.txt)', metavar='FILE', default='results.txt')
    ap.add_argument('-s', '--sensitivities', help='sensitivities file name (default: sensitivities.txt)', metavar='FILE', default='sensitivities.txt')
    ap.add_argument('-b', '--build', help='build/model directory (default: [BCMD_HOME]/build)', metavar='DIR')
    ap.add_argument('-o', '--outdir', help='work/output directory (default: [BUILD]/[MODEL_NAME]_[TIMESTAMP]', metavar='DIR')
    ap.add_argument('-p', '--perturb', help='enable input perturbation', action='store_true')
    ap.add_argument('-d', '--dryrun', help='dump configuration details without simulating', action='store_true')
    ap.add_argument('jobfile', help='job specification file')
    ap.add_argument('datafile', help='CSV containing time series data')

    args = ap.parse_args()

    config = CONFIG
    config['jobfile'] = args.jobfile
    config['datafile'] = args.datafile

    config['outfile'] = args.results
    config['sensitivities'] = args.sensitivities

    if args.build:
        config['build'] = args.build
    else:
        config['build'] = BUILD

    if args.outdir:
        config['work'] = args.outdir
    # otherwise leave as None and concoct after reading job file

    config['perturb'] = args.perturb
    config['dryrun'] = args.dryrun

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

        var = { 'name': name, 'post':[]}

        if name in aliases:
            dataname = aliases[name]
        else:
            dataname = name

        if dataname in data:
            var['points'] = np.array(data[dataname])

        if len(item) > 1:
            var['dist'] = item[1]

            if item[1] == 'constant' and len(item) > 2:
                var['value'] = float(item[2])
                if len(item) > 4:
                    var['default'] = float(item[4])
                else:
                    var['default'] = var['value']
                var['min'] = var['value']
                var['max'] = var['value']
            elif (item[1] == 'normal' or item[1] == 'lognormal') and len(item) > 2:
                var['mean'] = float(item[2])
                if len(item) > 3:
                    var['var'] = float(item[3])
                if len(item) > 4:
                    var['default'] = float(item[4])
                elif var['dist'] == 'lognormal':
                    var['default'] = np.exp(var['mean'])
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

    return result, names

# get job details from input files
def process_inputs(config):
    print 'Processing inputs'

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
                    if ',' in line:
                        pp = [x.strip() for x in line.split(',')]
                    else:
                        pp = line.split()

                    try:
                        dummy = float(pp[2])
                        params.append(pp)
                    except (ValueError, IndexError):
                        pass

    ins = job['header'].get('input', [])

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

    config['name'] = model
    config['program'] = job['header'].get('program', [[os.path.join(BUILD, model + '.model')]])[0][0]
    config['model_io'] = job['header'].get('model_io', [[os.path.join(workdir, 'model_io')]])[0][0]
    config['work'] = workdir
    config['outfile'] = os.path.join(workdir, config['outfile'])
    config['sensitivities'] = os.path.join(workdir, config['sensitivities'])
    config['info'] = os.path.join(workdir, config['info'])

    if not os.path.isfile(config['program']):
        raise Exception("model executable '%s' does not exist" % config['program'])

    if tname not in timedata:
        raise Exception("time step field '%s' not present in data file" % tname)

    config['times'] = timedata[tname]
    config['vars'], varnames = process_vars(vars, aliases, timedata)
    config['params'] = process_vars(params, aliases, timedata)

    if param_select != PARAM_SELECT:
        all_params = config['params']
        config['params'] = []
        for param in all_params:
            if param['name'] in param_select:
                config['params'].append(param)

    config['inputs'] = process_vars(ins, aliases, timedata)

    config['baseSeq'], dummy = steps.readFiles(job['header'].get('init', [[]])[0])
    config['divisions'] = int(job['header'].get('divisions', [[DIVISIONS]])[0][0])
    config['nbatch'] = int(job['header'].get('nbatch', [[NBATCH]])[0][0])
    config['job_mode'] = job['header'].get('job_mode', [[JOB_MODE]])[0][0]
    config['npath'] = int(job['header'].get('npath', [[NPATH]])[0][0])
    config['jump'] = int(job['header'].get('jump', [[JUMP]])[0][0])
    config['interference'] = int(job['header'].get('interference', [[INTERFERENCE]])[0][0])
    config['save_interval'] = int(job['header'].get('save_interval', [[SAVE_INTERVAL]])[0][0])
    config['delta'] = float(job['header'].get('delta', [[DELTA]])[0][0])

    if 'delta' in job['header'] and len(job['header']['delta'][0]) > 1:
        config['relative_delta'] = job['header']['delta'][0][1] == 'relative'

    config['timeout'] = int(job['header'].get('timeout', [[model_bcmd.TIMEOUT]])[0][0])

    # hack alert -- option for non-finite distances to be replaced with some real value
    config['substitute'] = float(job['header'].get('substitute', [[distance.SUBSTITUTE]])[0][0])
    distance.SUBSTITUTE = config['substitute']

    if config['perturb']:
        config['beta'] = int(job['header'].get('beta', [[BETA]])[0][0])
    else:
        # ignore multiple trials in config if not perturbing
        config['beta'] = 1

    # weight sums over vars for hessian jobs, for optim compatibility
    weights = job['header'].get('weight', {})
    for weight in weights:
        config['weights'][weight[0]] = float(weight[1])

    if 'sigma' in job['header']:
        config['sigma'] = float(job['header']['sigma'][0][0])

    # for the moment the only supported distance functions are in the distance module
    # if that's ever not the case this could be a bit trickier...
    if config['sigma'] is not None and job['header'].get('distance', [[DISTANCE]])[0][0] == 'loglik':
        config['distance'] = distance.loglikWithSigma(config['sigma'])
        print 'using sigma=%g' % config['sigma']
    else:
        config['distance'] = getattr(distance, job['header'].get('distance', [[DISTANCE]])[0][0])

    # record any posthoc transformations for optimisation variables
    posts = job['header'].get('post', [])
    for post in posts:
        if post[0] in varnames:
            ff = posthoc.get(post[1:])
            if ff is not None:
                config['vars'][varnames.index(post[0])]['post'].append(ff)
    return config

# build parameter combos for all job specs
def make_jobs(config):
    mode = config.get('job_mode', JOB_MODE)
    params = config['params'] + config['vars']

    print "Making jobs for mode '%s'" % mode

    if mode == 'cartesian':
        quants = [quantiles(p, config['divisions']) for p in params]
        result = cartesian(quants)
    elif mode == 'morris':
        result = morris(params, config)
    elif mode == 'fast':
        result = fast(params, config)
    elif mode == 'hessian':
        result = hessian(params, config)
    elif mode == 'pairwise':
        result = []
        for ii in range(len(params)):
            qi = quantiles(params[ii], config['divisions'])
            for jj in range(ii+1, len(params)):
                qj = quantiles(params[jj], config['divisions'])
                before = [x['default'] for x in params[:ii]]
                between = [x['default'] for x in params[(ii+1):jj]]
                after = [x['default'] for x in params[(jj+1):]]

                result.extend([before + [x] + between + [y] + after for x in qi for y in qj])
    else:
        result = []
        for ii in range(len(params)):
            before = [x['default'] for x in params[:ii]]
            after = [x['default'] for x in params[(ii+1):]]
            result.extend([ before + [x] + after for x in quantiles(params[ii], config['divisions'])])

    # pprint.pprint(result)

    print '%d jobs made' % len(result)

    return result

# construct a set of jobs corresponding to Morris trajectories
# (this is now deferred to SALib)
def morris(params, config):
    # specify problem in form understood by SALib
    config['problem'] = { 'num_vars': len(params),
                          'names': [p['name'] for p in params],
                          'groups': None,
                          'bounds': [[p.get('min',0), p.get('max',1)] for p in params] }

    result = SALib.sample.morris.sample(config['problem'],
                                        config['npath'],
                                        config['divisions'],
                                        config['jump'])
    return result

# construct a set of jobs for eFAST sensitivity analysis (via SALib)
def fast(params, config):
    # specify problem in form understood by SALib
    config['problem'] = { 'num_vars': len(params),
                          'names': [p['name'] for p in params],
                          'groups': None,
                          'bounds': [[p.get('min',0), p.get('max',1)] for p in params] }

    result = SALib.sample.fast_sampler.sample(config['problem'],
                                              config['npath'],
                                              config['interference'])
    return result

# construct a set of jobs to enable estimation of the Hessian
def hessian(params, config):
    if config['relative_delta']:
        for p in params:
            p['delta'] = np.max((p['min'], np.min((p['default'] + config['delta'] * (p['max'] - p['min'])))))
            p['delta2'] = np.max((p['min'], np.min((p['default'] + 2 * config['delta'] * (p['max'] - p['min'])))))
    else:
        for p in params:
            p['delta'] = np.max((p['min'], np.min((p['default'] + config['delta']))))
            p['delta2'] = np.max((p['min'], np.min((p['default'] + 2 * config['delta']))))

    # zero-order: start point
    result = [ [p['default'] for p in params] ]

    # first order: changing a single param
    for ii in range(len(params)):
        # point changing only this param
        job = [p['default'] for p in params]
        job[ii] = params[ii]['delta']
        result.append(job)

    # second order: changing pairs of params, or the same one twice
    for ii in range(len(params)):
        for jj in range(ii,len(params)):
            job = []
            for pp in range(len(params)):
                if pp == ii and pp == jj:
                    job.append(params[pp]['delta2'])
                elif pp == ii or pp == jj:
                    job.append(params[pp]['delta'])
                else:
                    job.append(params[pp]['default'])
            result.append(job)

    return result


# build model
def make_model(config):
    if config['dryrun']:
        return None

    print 'Creating wrapper for model %s' % config['name']

    model = model_bcmd.model_bcmd( name=config['name'],
                                   vars=config['vars'],
                                   params=config['params'],
                                   inputs=config['inputs'],
                                   times=config['times'],
                                   program=config['program'],
                                   baseSeq=config['baseSeq'],
                                   workdir=config['model_io'],
                                   timeout=config['timeout'],
                                   deleteWorkdir=False )
    return model

# run jobs with model
def run_jobs(model, jobs, config):
    result = []

    print 'Running jobs'

    batches, excess = divmod(len(jobs), config['nbatch'])

    print '%d jobs (%d batches of %d, with %d excess)' % (len(jobs), batches, config['nbatch'], excess)
    for ii in range(batches):
    	print 'Batch %d (%d to %d)' % (ii, ii * config['nbatch'], (ii+1) * config['nbatch'] - 1)
        params = [ jobs[x] for x in range(ii * config['nbatch'], (ii+1) * config['nbatch']) ]
        t0 = time.time()
        print 'Start: %s' % time.asctime(time.localtime(t0))
        result.append( model.simulate( params,
                                       config['times'],
                                       config['nbatch'],
                                       config['beta'],
                                       do_perturb=config['perturb'] ))
        t1 = time.time()
        print 'Completed: %s (%.2f seconds execution)' % (time.asctime(time.localtime(t0)), t1-t0)

        # optionally save periodic intermediate results
        # on the one hand this is potentially costly, on the other we'd rather
        # not lose days of processing...
        if config['save_interval'] > 0 and ii % config['save_interval'] == 0:
            print 'Saving intermediate results'
            output_results(jobs, np.vstack(result), config, True)

    if excess:
        print 'Running %d excess jobs' % excess
        params = [ jobs[x] for x in range(batches * config['nbatch'], len(jobs)) ]
        t0 = time.time()
        print 'Start: %s' % time.asctime(time.localtime(t0))
        result.append( model.simulate( params,
                                       config['times'],
                                       excess,
                                       config['beta'],
                                       do_perturb=config['perturb'] ))
        t1 = time.time()
        print 'Completed: %s (%.2f seconds execution)' % (time.asctime(time.localtime(t0)), t1-t0)


    # merge into a single multidim array whose first dimension is the job index
    # (ie, identifies the parameter set)
    result = np.vstack(result)
    print '%d result sets generated' % result.shape[0]
    return result


# output the results
# for the moment we just dump as tab-delim text to stdout
# eventually there will probably be configurable options
def output_results(jobs, results, config, intermediate=False):
    print 'Writing info file'
    with open(config['info'], 'w') as out:
        # this is tiresome, but needed to be able to read the file later
        distance = config['distance']
        config['distance'] = None

        pprint.pprint(config, stream=out)

        # ok, now we can restore it
        config['distance'] = distance

    print 'Writing results file'
    t0 = time.time()
    print 'Start: %s' % time.asctime(time.localtime(t0))
    with open(config['outfile'], 'w') as out:
        nparams = len(jobs[0])
        nbatch = config['nbatch']
        ntimes = len(config['times'])

        header = [ 'job', 'rep', 'species' ]
        header.extend( [ p['name'] for p in config['params'] + config['vars'] ] )
        header.extend( [ 't%d' % ii for ii in range(len(config['times'])) ] )

        print >> out, '\t'.join(header)

        timeline = [ 'NA', 'NA', 't' ]
        timeline.extend( ['NA'] * nparams )
        timeline.extend( [ str(t) for t in config['times'] ] )

        print >> out, '\t'.join(timeline)

        for input in config['inputs']:
            inline = [ 'NA', 'NA', input['name'] + '_in' ]
            inline.extend( ['NA'] * nparams )
            inline.extend( [ str(v) for v in input['points'] ] )
            print >> out, '\t'.join(inline)

        for var in config['vars']:
            varline = [ 'NA', 'NA', var['name'] + '_out' ]
            varline.extend( ['NA'] * nparams )
            pts = var.get('points', [])
            varline.extend( [ str(v) for v in pts ] )
            varline.extend( ['NA'] * (len(config['times']) - len(pts)) )
            print >> out, '\t'.join(varline)

        for job in range(results.shape[0]):
            for rep in range(results.shape[1]):
                for species in range(results.shape[3]):
                    row = [ str(job), str(rep), config['vars'][species]['name'] ]
                    row.extend( [ str(p) for p in jobs[job] ] )
                    row.extend( [ str(v) for v in results[job, rep, :, species] ] )

                    print >> out, '\t'.join(row)

    t1 = time.time()
    print 'Completed: %s (%.2f seconds to write)' % (time.asctime(time.localtime(t0)), t1-t0)

    # for sensitivity jobs, calculate sensitivities for each output and dump those too
    if config.get('job_mode', JOB_MODE) in ('morris', 'fast', 'hessian')  and not intermediate:
        postproc(jobs, results, config)


# do postprocessing on the simulation results
# -- ie, for each output, calculate distance metric and then work out sensitivity or hessian
def postproc(jobs, results, config):
    collated = {}
    print 'Post-processing job results'
    for var in config['vars']:
        name = var['name']
        pts = var.get('points', np.zeros(len(config['times'])))

        for post in var.get('post'):
            pts = post(pts)
        collated[name] = { 'target': pts,
                           'distances': [] }

    summed = []

    print 'Calculating distances'
    for job in range(results.shape[0]):
        for rep in range(results.shape[1]):
            sumdist = 0
            for species in range(results.shape[3]):
                name = config['vars'][species]['name']
                cv = collated[name]
                dist = config['distance'](cv['target'], results[job, rep, :, species])
                cv['distances'].append(dist)
                sumdist += dist * config['weights'].get(name, 1)
            summed.append(sumdist)

    if config['job_mode']=='hessian':
        summed
        process_hessian(jobs, np.array(summed), config)
    else:
        process_SA(jobs, collated, config)

# sensitivity analysis
def process_SA(jobs, collated, config):
    for var in collated:
        print 'Calculating sensitivities for variable %s' % var
        collated[var]['distances'] = np.array(collated[var]['distances'])

        if config['job_mode']=='morris':
            collated[var]['sensitivities'] = SALib.analyze.morris.analyze(config['problem'],
                                                                          jobs,
                                                                          collated[var]['distances'],
                                                                          num_levels=config['divisions'],
                                                                          print_to_console=True,
                                                                          grid_jump=config['jump'])
        elif config['job_mode']=='fast':
            collated[var]['sensitivities'] = SALib.analyze.fast.analyze(config['problem'],
                                                                        collated[var]['distances'],
                                                                        config['interference'],
                                                                        print_to_console=True)

    print 'Writing sensitivities to file %s' % config['sensitivities']

    # ok, now print the wretched things to yet another tab-delimited file

    # tailor the output according to job type
    fields = { 'morris': ['mu', 'mu_star', 'sigma', 'mu_star_conf'],
               'fast': ['S1', 'ST'] }.get(config['job_mode'], [])
    with open(config['sensitivities'], 'w') as f:
        header = ['Parameter']
        for var in collated:
            header.extend(['%s_%s' % (var, x) for x in fields])
        print >> f, '\t'.join(header)

        prms = [ p['name'] for p in config['params'] + config['vars'] ]
        for ii in range(len(prms)):
            row = [prms[ii]]
            for var in collated:
                row.extend([str(collated[var]['sensitivities'][x][ii]) for x in fields])
            print >> f, '\t'.join(row)

# estimate hessian matrix for each output
def process_hessian(jobs, summed, config):
    params = config['params'] + config['vars']
    N = len(params)

    # denominator is shared by all signals
    denom = np.zeros((N,N))
    for ii in range(N):
        for jj in range(N):
            # this will be wrong if too near the bounds
            denom[(ii,jj)] = (params[ii]['delta'] - params[ii]['default']) * (params[jj]['delta'] - params[jj]['default'])

    base = summed[0]
    first = np.zeros(N)
    numer = np.zeros((N,N))

    for ii in range(N):
        first[ii] = summed[ii + 1]

    idx = N + 1
    for ii in range(N):
        for jj in range(ii,N):
            numer[(ii,jj)] = summed[idx] + base - first[ii] - first[jj]
            numer[(jj,ii)] = numer[(ii,jj)]
            idx += 1

    # factors that do not vary cannot have effects,
    # so we artificially force gradient to be zero
    numer[denom==0] = 0
    denom[denom==0] = 1

    hess = numer/denom

    with open(os.path.join(config['work'],'Hessian.txt'), 'wb') as f:
        print >> f, '\t'.join([p['name'] for p in params])
        for ii in range(N):
            print >> f, '\t'.join([str(x) for x in hess[ii]])


# main entry point
# provide a job file and a data file
if __name__ == '__main__':
    config = process_args()
    if config:
        process_inputs(config)
        model = make_model(config)
        jobs = make_jobs(config)

        if model:
            results = run_jobs(model, jobs, config)
            output_results(jobs, results, config)

        else:
            print 'CONFIG:'
            pprint.pprint(config)
            print '----------'
            print 'JOBS:'
            pprint.pprint(jobs)
