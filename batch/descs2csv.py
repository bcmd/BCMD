#!/usr/bin/env python

# simple script to read item descriptions from a BRAINCIRC model file
# and write them out (for the moment as a CSV)

import sys, os, os.path
import csv
import pprint

def readDescs(file, types=['V', 'P', 'PROC'], merge=True):
    result = {}
    if merge: segment = {}
    with open(file) as f:
        lines = f.readlines()
    
    for ii in range(len(lines)):
        lines[ii] = lines[ii].strip('\t\n\r ')
    
    for type in types:
        if not merge:
            segment = {}
        
        ii = 0
        while ii < len(lines) and lines[ii] != (type + 'DESC'):
            ii = ii + 1
        
        ii = ii + 1
        
        while ii < len(lines) and lines[ii] != ('end' + type + 'DESC'):
            block = []
            while ii < len(lines) and lines[ii] != '******':
                block.append(lines[ii])
                ii = ii + 1
            
            ii = ii + 1
            
            if len(block) > 1:
                block[0] = 'name:' + block[0]
                block[1] = 'desc:' + block[1]
            
                blockdict = bcStringsToDict(block)
                segment[blockdict['name']] = blockdict
            
        if not merge:
            result[type] = segment
        
    if merge:
        return segment
    
    return result

def bcStringsToDict(bc):
    result = {}
    for line in bc:
        if ':' in line:
            div = line.split(':')
            field = div[0].strip()
            result[field] = div[1].strip()
    return result

def writeDescsToCSV(descs, file, merged=True):
    if merged:
        keys = conformKeys(descs)
        
        with open(file, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            
            for name in descs:
                item = descs[name]
                writer.writerow([item[key] for key in keys])
    
    # TODO: handle unmerged case

def conformKeys(descs):
    keys = set()
    for name in descs:
        keys = keys | set(descs[name].keys())
    
    keys = [x for x in keys]
    
    for name in descs:
        item = descs[name]
        for key in keys:
            if key not in item:
                item[key] = ''
    
    return keys

if __name__ == '__main__':
    # TODO: support unmerged case
    for name in sys.argv[1:]:
        descs = readDescs(name)
        writeDescsToCSV(descs, name + '.csv')



