#!/usr/bin/env python

# utility hack to merge the postprocessed elementaries from multiple Morris runs
# we assume they've all been run with the same set of parameters and thus have
# consistent columns

import sys, os, os.path

BRIEF='brief.txt'
ELEMENTARIES='elementaries.txt'
AGGREGATE='aggregate.txt'
PREFIX_HEADER='ID\tinput'

def aggregate(sub, target, header, idx):
    print 'aggregating ' + sub
    with open(os.path.join(sub, BRIEF)) as f:
        # this will break if we change the format of BRIEF    
        input = f.readline().strip().split()[-1].split('/')[-1]
    
    with open(os.path.join(sub, ELEMENTARIES)) as f:
        first = True
        for line in f:
            if first:
                first = False
                if header:
                    print >> target, PREFIX_HEADER + '\t' + line.strip()
            else:
                print >> target, str(idx) + '\t' + input + '\t' + line.strip()

if __name__ == '__main__':
    # later there'll probably be some config options, but for now...
    dir = sys.argv[1]
    
    subdirs = [os.path.join(dir,name) for name in os.listdir(dir) if os.path.isdir(os.path.join(dir,name))]    
    with open(os.path.join(dir, AGGREGATE), 'w') as f:
        header=True
        idx = 1
        for sub in subdirs:
            aggregate(sub, f, header, idx)
            header=False
            idx = idx + 1
