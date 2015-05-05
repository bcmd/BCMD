#!/usr/bin/env python

import sys, os, os.path
import numpy
import pprint

import distance
import inputs

# sensitivity analyses
import SALib.analyze.morris
import SALib.analyze.fast

from numpy import nan
from numpy import array

# filenames
INFO='dsim.info'
BRIEF='brief.txt'
RESULTS='results.txt'
DISTANCES='distances.txt'
SENSITIVITIES='SA.txt'
MEASURED='measured.txt'
JOBS='jobs.txt'

# notable headers
T0 = 't0'
SPECIES = 'species'

# identifying reference traces -- this is arguably dodgy, but it's
# what dsim uses, so...
OUT_SUFFIX = '_out'

# distances
DIST_HEADS = ['dist_L1', 'dist_L2', 'dist_Mean', 'dist_LogLik', 'dist_Cosine', 'dist_Angle']
DIST_FUNCS = [distance.manhattan, distance.euclidean, distance.meandist, distance.loglik, distance.cosine, distance.angular]
INF = float('Inf')
NAN = float('nan')
ALL_NAN = ['nan'] * len(DIST_HEADS)
ALL_INF = [INF] * len(DIST_HEADS)

# substitution policy
# TODO: make this configurable
SUBSTITUTE = 0

THRESH = 1e-10

def postproc(dir):
    print 'processing directory: ' + dir
    info = readInfo(dir)
    if info:
        writeBrief(dir, info)
        config = getConfig(info)
        calcDistances(dir, config)
    else:
        print 'unable to open info file, skipping directory'

def readInfo(dir):
    infofile = os.path.join(dir, INFO)
    if os.path.isfile(infofile):
        with open(infofile) as f:
            info = eval(f.read())
        return info
    return None

# attempt to load comparison traces from an external file
def getMeasured(dir, config):
    measured = {}
    ts = {}
    filename = os.path.join(dir, MEASURED)
    if os.path.isfile(filename):
        print 'attempting to load measured.txt'
        ts = inputs.readCSV(filename, False)
        
    for name in config['target']:
        if name in ts:
            print 'external measurement sequence loaded for variable %s' % name
            measured[name] = numpy.array(ts[name])
        else:
            measured[name] = []
    return measured

def writeBrief(dir, info):
    with open(os.path.join(dir, BRIEF), 'w') as f:
            print >> f, 'datafile: ' + info['datafile']
            # add any other info as desired here

def getConfig(info):
    target = [ x['name'] for x in info['vars'] ]
    measured = [ x + OUT_SUFFIX for x in target ]
    return { 'target':target,
             'measured':measured,
             'info':info,
             'substitute':SUBSTITUTE }

def calcDistances(dir, config):
    
    distance.SUBSTITUTE = config['substitute']
    
    resultsfile = os.path.join(dir, RESULTS)
    distancesfile = os.path.join(dir, DISTANCES)
    saFile = os.path.join(dir, SENSITIVITIES)
    jobsFile = os.path.join(dir, JOBS)
    
    if os.path.isfile(resultsfile):
        # set up a bunch of stuff we'll need
        header = None
        speciesIndex = -1
        t0Index = -1

        # stuff we will need to extract from the header
        
        # NB: in a potentially-confusing move, we key the measurements list by the target
        # species, on the basis that that's what we actually care about -- the _out
        # suffix is just a way to get that data into this dict
        # -- in any case, we attempt to load external data here, but don't fill
        # in defaults until later, when we know how long the result traces are...
        measured = getMeasured(dir, config)
        
        # assume that all species are run with the same list of jobs
        # and we'll use those for the first target
        jobs = []
        params = None
        
        distances = {}
        for species in config['target']:
            distances[species] = {}
            for dist in DIST_HEADS:
                distances[species][dist] = []
        
        # calculate and write out distances for all jobs (species will be interleaved, as in the original results)
        with open(resultsfile) as results, open(distancesfile, 'w') as distOut:
            
            for line in results:
                row = line.strip().split('\t')
                
                # header row
                if speciesIndex < 0:
                    header = row
                    speciesIndex = row.index(SPECIES)
                    t0Index = row.index(T0)
                    params = row[(speciesIndex+1):t0Index]
                    
                    print >> distOut, '\t'.join(row[:t0Index] + DIST_HEADS)
                    
                    # add a default zero array for all measured, in case they're not provided
                    UNMEASURED = numpy.zeros(len(row[t0Index:]))
                    for name in config['target']:
                        # distance funcs fail with mismatched lengths, so we replace
                        # an external traces that aren't the right length -- this should
                        # inlude any absentees
                        if len(measured[name]) == 0:
                            measured[name] = UNMEASURED
                        elif len(measured[name]) != len(UNMEASURED):
                            print 'incorrect length (%d) for variable %s, substituting zero default' % (len(measured[name]), name)
                            measured[name] = UNMEASURED
                
                else:
                    species = row[speciesIndex]
                    
                    # measured data
                    if species in config['measured']:
                        
                        # when there is no measured data, the row will be filled with NA
                        # since we cannot measure distances in that case, we ignore it
                        # and keep the default zeros instead
                        if not 'NA' in row[t0Index:]:
                            # see note above about keying -- we strip the suffix here
                            print 'using measured data %s from results file as target for %s' % (species, species[:-len(OUT_SUFFIX)])
                            measured[species[:-len(OUT_SUFFIX)]] = numpy.array([float(x) for x in row[t0Index:]])
                
                    # simulation data -- calculate distances and write out
                    elif species in config['target']:
                    
                        # extract the job details (first species only)
                        if species==config['target'][0]:
                            jobs.append(numpy.array([float(x) for x in row[(speciesIndex+1):t0Index]]))
                        
                        # calculate the range of distance metrics between this sim and the measured data
                        simdata = numpy.array([float(x) for x in row[t0Index:]])
                        dists = [ df(measured[species], simdata) for df in DIST_FUNCS ]
                        print >> distOut, '\t'.join(row[:t0Index] + [str(d) for d in dists])
                        
                        # save as vectors per metric per species, for possible use as a sensitivity Y
                        for ii in range(len(dists)):
                            distances[species][DIST_HEADS[ii]].append(dists[ii])
        
        # write the jobs list
        with open(jobsFile, 'w') as jf:
            print >> jf, '\t'.join(params)
            for job in jobs:
                print >> jf, '\t'.join([str(x) for x in job])
        
        # calculate and write sensitivities according to job type
        if config['info']['job_mode'] == 'morris':
            fields = ['mu', 'mu_star', 'sigma', 'mu_star_conf']
            with open(saFile, 'w') as sf:
                print >> sf, '\t'.join(['Species', 'Metric', 'Param'] + fields)
                
                for species in config['target']:
                    for dist in DIST_HEADS:
                        Y = numpy.array(distances[species][dist])
                        sens = SALib.analyze.morris.analyze(config['info']['problem'],
                                                            jobs,
                                                            Y,
                                                            num_levels=config['info']['divisions'],
                                                            print_to_console=True,
                                                            grid_jump=config['info']['jump'])
                        for ii in range(len(params)):
                            print >> sf, '\t'.join([species, dist, params[ii]] + [str(sens[x][ii]) for x in fields])
        
        elif config['info']['job_mode'] == 'fast':
            fields = ['S1', 'ST']
            with open(saFile, 'w') as sf:
                print >> sf, '\t'.join(['Species', 'Metric', 'Param'] + fields)
                
                for species in config['target']:
                    for dist in DIST_HEADS:
                        Y = numpy.array(distances[species][dist])
                        sens = SALib.analyze.fast.analyze(config['info']['problem'],
                                                          Y,
                                                          config['info']['interference'],
                                                          print_to_console=True)
                        for ii in range(len(params)):
                            print >> sf, '\t'.join([species, dist, params[ii]] + [str(sens[x][ii]) for x in fields])        

def printUsage():
    print 'Usage: ' + sys.argv[0] + ' DIR'
    print '    DIR = directory containing results, or subdirectories of results'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        printUsage()
        sys.exit()
    
    dir = sys.argv[1]
    
    if os.path.isfile(os.path.join(dir,INFO)):
        print "Attempting to process single results directory"
        postproc(dir)
    else:
        print "Attempting to processing subdirectories"
        subdirs = [os.path.join(dir,name) for name in os.listdir(dir) if os.path.isdir(os.path.join(dir,name))]
        for sub in subdirs:
            postproc(sub)
