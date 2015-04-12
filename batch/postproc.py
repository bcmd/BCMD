#!/usr/bin/env python

import sys, os, os.path
import numpy
import pprint

import distance
import inputs

# filenames
INFO='dsim.info'
BRIEF='brief.txt'
RESULTS='results.txt'
DISTANCES='distances.txt'
ELEMENTARIES='elementaries.txt'
MEASURED='measured.txt'

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
    # for the moment, config consists only of target and measured fields
    target = [ x['name'] for x in info['vars'] ]
    measured = [ x + OUT_SUFFIX for x in target ]
    return { 'target':target, 'measured':measured }

def calcDistances(dir, config):
    resultsfile = os.path.join(dir, RESULTS)
    distancesfile = os.path.join(dir, DISTANCES)
    elemsFile = os.path.join(dir, ELEMENTARIES)
    
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
        
        # previous rows, for checking stepwise changes
        prevRow = {}
        for name in config['target']: prevRow[name] = None
        
        # previous distances, for ditto -- prefilling is probably unnecessary here, but for clarity
        prevDists = {}
        for name in config['target']: prevDists[name] = None

        # elementary effects for each target
        elementaries = {}
        for name in config['target']: elementaries[name] = {}
        
        # ok, let's proceed
        with open(resultsfile) as results, open(distancesfile, 'w') as distances:
            
            for line in results:
                row = line.strip().split('\t')
                
                # header row
                if speciesIndex < 0:
                    header = row
                    speciesIndex = row.index(SPECIES)
                    t0Index = row.index(T0)
                    
                    print >> distances, '\t'.join(row[:t0Index] + DIST_HEADS)
                    
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
                    
                        # distances are not defined for traces containing NaNs
                        if 'nan' in row:
                            print >> distances, '\t'.join(row[:t0Index] + ALL_NAN)
                            dists = ALL_INF
                        else:
                            simdata = numpy.array([float(x) for x in row[t0Index:]])
                            dists = [ df(measured[species], simdata) for df in DIST_FUNCS ]
                            print >> distances, '\t'.join(row[:t0Index] + [str(d) for d in dists])
                    
                        # map parameter changes to distance changes
                        if prevRow[species] is None:
                            prevRow[species] = numpy.array([float(x) for x in row[(speciesIndex + 1):t0Index]])
                            prevDists[species] = dists
                        else:
                            currRow = numpy.array([float(x) for x in row[(speciesIndex + 1):t0Index]])
                            diffs = [ abs(x) > THRESH for x in (currRow - prevRow[species]) ]
                            
                            # each Morris trajectory changes one param at a time
                            # multiple changes indicate the start of a new trajectory, so we do not
                            # calculate elementaries in that case
                            # (we are duplicating some effort here, since all species will start a new trajectory
                            # at the same time, but avoiding that would be far more trouble than its worth...)
                            if diffs.count(True) == 1:
                                changed = header[diffs.index(True) + speciesIndex + 1]
                                distChanges = [ prevDists[species][ii] - dists[ii] for ii in range(len(dists))]
                                
                                if changed in elementaries[species]:
                                    elems = elementaries[species][changed]
                                    for ii in range(len(DIST_HEADS)):
                                        elems[DIST_HEADS[ii]].append(distChanges[ii])
                                else:
                                    elems = {}
                                    for ii in range(len(DIST_HEADS)):
                                        elems[DIST_HEADS[ii]] = [distChanges[ii]]
                                    elementaries[species][changed] = elems
                        
                            prevRow[species] = currRow
                            prevDists[species] = dists
        
        for species in config['target']:
            for elem in elementaries[species]:
                dists = elementaries[species][elem]
                mu = {}
                mu_star = {}
                sigma = {}
                Nmax = 0
                for head in DIST_HEADS:
                    vals = (numpy.array(dists[head]))
                    finvals = vals[numpy.isfinite(vals)]
                    N = len(finvals)
                    if N > 0:
                        mu[head] = numpy.mean(finvals)
                        mu_star[head] = numpy.mean(numpy.abs(finvals))
                        sigma[head] = numpy.std(finvals)
                        Nmax = max(Nmax, N)
                    else:
                        mu[head] = NAN
                        mu_star[head] = NAN
                        sigma[head] = NAN
                dists['mu'] = mu
                dists['mu_star'] = mu_star
                dists['sigma'] = sigma
                dists['N'] = Nmax
        
        with open(elemsFile, 'w') as f:
            print >> f, '\t'.join(['Species', 'Param', 'N'] + [ x + '_' + y for x in DIST_HEADS for y in ['mu', 'mu_star', 'sigma']])
            for species in config['target']:
                for name in elementaries[species]:
                    row = [species, name]
                    dicts = elementaries[species][name]
                    row.append(str(dicts['N']))
                    for head in DIST_HEADS:
                        row.append(str(dicts['mu'][head]))
                        row.append(str(dicts['mu_star'][head]))
                        row.append(str(dicts['sigma'][head]))
                    print >> f, '\t'.join(row)

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
