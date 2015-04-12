#! /usr/bin/env python
# utility to convert the awkward stderr debugging outputs from a model
# into a more useable format

import sys, os
import csv

def readModelLog ( filename ):
    # first entry just contains all the names, with values = None
    # subsequent entries are dicts assigning values
    result = [ { '00_msg': None, '01_t': None, '02_errs': None } ]

    # for the moment, we just assume the independent variable is called t    
    t = '0'
    current = {}
    
    with open(filename) as f:
        for line in f:
            # lines starting with '#' are messages, which are stored in special field '00_msg'
            if line.startswith('#'):
                if current:
                    result.append(current)
                    current = {}
                current['00_msg'] = line.strip()
                
            # lines starting with '*' are RHS steps, and should specify t as the last thing on the line, after an '='
            elif line.startswith('*'):
                if current:
                    result.append(current)
                    current = {}
                t = line.split('=')[1].strip()
                current['01_t'] = t
                current['00_msg'] = line.strip()
            
            # any other line with an equals sign should be a value assignment
            elif '=' in line:
                name, value = [x.strip() for x in line.split('=')]
                result[0][name] = None
                current[name] = value
            
            # any other line is an extraneous error message that we don't really care about, but might as well stash it
            else:
                if '02_errs' in current:
                    # cheesy hack to include multiple messages within a single CSV entry
                    current['02_errs'] = current['02_errs' + ';' + line]
                else:
                    current['02_errs'] = [line]
    
    return result

# for the moment, output is always to stdout
def writeLogAsCSV ( log ):
    names = sorted(log[0].keys())
    
    print ','.join( ['"%s"' % x for x in names] )
    
    for row in log[1:]:
        print ','.join([ '"%s"' % x for x in [ row.get(y, '') for y in names]])


# invocation
if __name__ == '__main__':
    log = readModelLog(sys.argv[1])
    writeLogAsCSV(log)
