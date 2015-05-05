# abc-sysbio compatible wrapper class for BCMD models

import numpy
import numpy.random
import tempfile
import shutil
import csv
import os
import copy
import sys

import steps
import distance
import abortable

from multiprocessing import Process, Queue

# default timeout, in seconds
TIMEOUT = 30

# translate prior specs into the (abcsmc) expected numeric triplets
def translate_prior( param ):
    prior = [0, 0, 0]
    
    dist = param.get('dist', None)
    
    if ( dist == 'constant' ):
        prior[1] = param.get('value', 0)
    elif ( dist == 'normal' ):
        prior[0] = 1
        prior[1] = param.get('mean', 0)
        prior[2] = param.get('var', 1)
    elif ( dist == 'uniform'):
        prior[0] = 2
        prior[1] = param.get('min', 0)
        prior[2] = param.get('max', 1)
    elif ( dist == 'lognormal' ):
        prior[0] = 3
        prior[1] = param.get('mean', 0)
        prior[2] = param.get('var', 1)
    
    return prior

# generate random values from an abcsmc-style distribution
# TODO: numpy.random.(log)normal uses SD rather than var
#       work out whether anything needs var, and if not switch to
#       SD so we don't have to do this stupid sqrt-ing
def sample(n, triplet):
    result = numpy.zeros(n)
    if triplet[0] == 0:
        result[:] = triplet[1]
    elif triplet[0] == 1:
        result[:] = numpy.random.normal(triplet[1], numpy.sqrt(triplet[2]), n)
    elif triplet[0] == 2:
        result[:] = numpy.random.uniform(triplet[1], triplet[2], n)
    elif triplet[0] == 3:
        result[:] = numpy.random.lognormal(triplet[1], numpy.sqrt(triplet[2]), n)
    return result

# outer function to run a single model invocation and queue its results
# for use when running multiple processes in parallel
def bcmd_proc (beta, n, params, queue, do_perturb, obj):
    # create the input file
    seq = obj.baseSeq[:]
    seq += steps.abcParamSequence(obj.initnames, params)
    seq += steps.makeSteadySequence(True)
    seq += steps.abcAbsoluteSequence(obj.times, obj.perturb(do_perturb), obj.vars, outhead=False)
    input = os.path.join(obj.workdir, '%s_%d_%d.input' % (obj.name, n, beta))
    steps.writeSequence(seq, input)

    output = os.path.join(obj.workdir, '%s_%d_%d.out' % (obj.name, n, beta))
    
    if obj.suppress:
        # invoke the model
        succ = abortable.call([obj.program, '-i', input, '-o', output], stdout=obj.DEVNULL, stderr=obj.DEVNULL, timeout=obj.timeout )    
    else:
        # create files to hold log values
        stdoutname = os.path.join(obj.workdir, '%s_%d_%d.stdout' % (obj.name, n, beta))
        stderrname = os.path.join(obj.workdir, '%s_%d_%d.stderr' % (obj.name, n, beta))
        try: f_out = open(stdoutname, 'w')
        except IOError: f_out = None
        
        try: f_err = open(stderrname, 'w')
        except IOError: f_err = None
    
        # invoke the model
        succ = abortable.call([obj.program, '-i', input, '-o', output], stdout=f_out, stderr=f_err, timeout=obj.timeout )
   
        if f_out: f_out.close()
        if f_err: f_err.close()

    # read the results
    result = numpy.zeros([len(obj.times), obj.nspecies])
    ii = 0
    if succ:
        with open(output, 'rb') as tabfile:
            reader = csv.reader(tabfile, delimiter='\t')
            for row in reader:
                # first entry in each row is the RADAU5 return code
                result[ii, :] = [float(x) for x in row[1:]]
                ii += 1
    else:
        result[:] = float('nan')
    
    # send them back to the master process
    queue.put({'n': n, 'data': result})

class model_bcmd:

    # constructor -- just record all the crap we'll need
    def __init__( self,
                  name,
                  vars,                    # outputs of simulation, to be compared with recorded data
                  params,                  # these get drawn by ASB at start of sim
                  inputs,                  # inputs set along the way from recorded data
                  times,
                  program,
                  fixed = [],              # constant parameters that should always be set
                  baseSeq = [],            # an initial step sequence in case we want to prepend stuff like like resets and steadying
                  workdir=None,            # default is to create a temp directory
                  deleteWorkdir=False,     # not quite sure when the best time for this is, probably in __del__?
                  suppress=True,           # suppress stdout and stderr in subprocesses
                  reseed=True,             # reseed the random number generator
                  steady=1000,
                  timeout=TIMEOUT,
                  debug=False
                ):
        
        self.name = name
        self.vars = vars
        self.nspecies = len(vars)
        self.parameters = params                               # includes info about priors
        self.nparameters = len(params) + len(vars)             # this is kind of daft, but ASB seems to assume species initial conditions will be appended to params
        
        self.prior = [ translate_prior(x) for x in params + vars ]
        
        self.times = times
        self.inputs = inputs
        self.program = program
        self.baseSeq = baseSeq
        
        self.vdefaults = [ x['default'] for x in vars ]
        
        self.pnames = [ x['name'] for x in params ]
        self.vnames = [ x['name'] for x in vars ]
        self.initnames = self.pnames + self.vnames
        
        self.fixed = fixed
        self.fixnames = [ x['name'] for x in fixed ]
        self.fixvals = numpy.array([ x['default'] for x in fixed ])
        
        self.have_perturbations = any([ p.get('dist', '') in ['normal', 'uniform'] for p in inputs ])
        
        # we'll always arrange for output to match data, so default behaviour should be correct
        self.fit = None
        
        # we need working space; we may want to kill it later
        self.deleteWorkdir = deleteWorkdir
        
        if workdir:
            self.workdir = workdir
            if not os.path.exists(workdir):
                os.makedirs(workdir)
        else:
            self.workdir = tempfile.mkdtemp(prefix=name)
        
        self.suppress = suppress
        if suppress:
            self.DEVNULL = open(os.devnull, 'wb')
        
        self.reseed = reseed
        self.steady = steady
        self.timeout = timeout
        self.debug = debug
    
    # destructor -- clean up
    def __del__( self ):
        if self.workdir and self.deleteWorkdir:
            shutil.rmtree(self.workdir, ignore_errors=True)
        
        if self.suppress and self.DEVNULL:
            self.DEVNULL.close()
    
    # get the configured model as an optimisable function
    # for the moment we assume n=1, beta=1
    # if no comparison data has been provided, reference level is 0 (ie distance = signal)
    # result is the weighted sum of distances (or just the straight sum if weights aren't provided)
    def optimisable ( self,
                      dist=distance.euclidean,
                      weights=[],
                      debug=False ):
        if debug:
            def f ( p ):
                print >> sys.stderr, p
                print >> sys.stderr, [ x['name'] for x in self.parameters ]
        
        else:
            # the function to optimise
            # all being well, this should be a closure with access
            # to the surrounding ivars (if not, we're buggered)
            def f ( p ):
                sim = self.simulate ( [numpy.concatenate((p,self.vdefaults))],
                                      t=self.times,
                                      n=1,
                                      beta=1,
                                      do_perturb=False )
                tot = 0
                for ii in range(len(self.vars)):
                    target = self.vars[ii].get('points',0)
                    signal = sim[0,0,:,ii]
                    for post in self.vars[ii]['post']:
                        signal = post(signal)
                    
                    dd = dist(signal, target)
                    
                    if self.debug:
                        print >> sys.stderr, 'distance due to %s: %f' % (self.vnames[ii], dd)
                
                    if weights and len(weights) > ii:
                        tot += weights[ii] * dd
                    else:
                        tot += dd
                        
                if self.debug:
                    print >> sys.stderr, 'total distance: %f' % tot
                return tot
        
        return f
    
    # set up, call out to run the actual simulation(s), read and collate the results
    def simulate( self,
                  p,                    # parameter values drawn by abcsmc (a list of n lists)
                  t,                    # the time points to simulate -- we're going to make the possibly-wrong assumption that these always stay as originally specified
                  n,                    # number of parallel simulations, as passed into abcsmc
                  beta,                 # number of runs with a particular param draw -- potentially useful if perturbing, since that makes the model non-deterministic
                  do_perturb=True ):    # include perturbations if in spec (set False to override)
        result = numpy.zeros([n, beta, len(t), self.nspecies])
        
        if n == 1:
            for ii in range(beta):
                input = self.writeInput(ii, 0, p[0], do_perturb)
                if self.debug:
                    print >> sys.stderr, 'simulate: running job %d' % ii
                output = self.run(ii, 0, input)
                result[0, ii, :, :] = self.readResults(output)
        else:
            for ii in range(beta):
                processes = []
                queue = Queue()
                for jj in range(n):
                    processes.append(Process(target=bcmd_proc,
                                             args=(ii, jj, p[jj], queue, do_perturb, self)))
                for proc in processes:
                    proc.start()
                
                for jj in range(n):
                    partial = queue.get()
                    result[partial['n'], ii, :, :] = partial['data']
        
        return result
    
    # write a BCMD input for our configured simulation
    # returns the name of the file
    def writeInput(self, id_beta, id_n, params, do_perturb=True):
        seq = self.baseSeq[:]
        
        names = self.initnames + self.fixnames
        vals = numpy.concatenate((params, self.fixvals))
        
        seq += steps.abcParamSequence(names, vals)
        seq += steps.abcAbsoluteSequence(self.times, self.perturb(do_perturb), self.vars, outhead=False, steady=self.steady)
        
        filename = os.path.join(self.workdir, '%s_%d_%d.input' % (self.name, id_n, id_beta))
        steps.writeSequence(seq, filename)
        
        return filename
    
    # run the BCMD model with the generated input file
    # returns the name of the (coarse) results file
    def run(self, id_beta, id_n, input):
        outname = os.path.join(self.workdir, '%s_%d_%d.out' % (self.name, id_n, id_beta))
        
        if self.suppress:
            # invoke the model program as a subprocess
            succ = abortable.call([self.program, '-i', input, '-o', outname], stdout=self.DEVNULL, stderr=self.DEVNULL, timeout=self.timeout )
        else:
            stdoutname = os.path.join(self.workdir, '%s_%d_%d.stdout' % (self.name, id_n, id_beta))
            stderrname = os.path.join(self.workdir, '%s_%d_%d.stderr' % (self.name, id_n, id_beta))
        
            # if opening these files fails, we may be in trouble anyway
            # but don't peg out just because of this -- let the the failure happen somewhere more important
            try: f_out = open(stdoutname, 'w')
            except IOError: f_out = None
        
            try: f_err = open(stderrname, 'w')
            except IOError: f_err = None
        
            # invoke the model program as a subprocess
            succ = abortable.call([self.program, '-i', input, '-o', outname], stdout=f_out, stderr=f_err, timeout=self.timeout )
        
            if f_out: f_out.close()
            if f_err: f_err.close()
        return outname
    
    
    # read the specified results file and return its data as a [len(t) x nspecies] numpy array
    # output should be a tab-delim text file; we assume consistency with our input spec
    # (this may be incorrect if spec includes output fields not in model -- probably ought
    # to do an initial sanity check on the model symbol table...)
    def readResults(self, output):
        result = numpy.zeros([len(self.times), self.nspecies])
        ii = 0
        with open(output, 'rb') as tabfile:
            reader = csv.reader(tabfile, delimiter='\t')
            for row in reader:
                # first entry in each row is the RADAU5 return code (tsk)
                result[ii, :] = [float(x) for x in row[1:]]
                ii += 1
        
        return result
    
    # generate a perturbed version of the input data
    def perturb(self, do_perturb=True):
        if do_perturb and self.have_perturbations:
            perturbed = copy.deepcopy(self.inputs)
            
            # this seems to be necessary because the same random state gets
            # inherited by multiple forks, resulting in all trajectories
            # getting identically perturbed, which rather defeats the purpose...
            if self.reseed:
                numpy.random.seed()
            
            for input in perturbed:
                input['points'] = sample(len(input['points']), translate_prior(input)) + input['points']
            return perturbed
        else:
            return self.inputs
    
