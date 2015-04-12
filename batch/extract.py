#!/usr/bin/env python

# yet another very simple hack to extract rows from a TXT/CSV file based on the value of (for the moment) one column

import sys, os, os.path

def extract (src, dst, col, val):
    print 'opening files'
    with open(src) as s, open(dst, 'w') as d:
        line = s.readline().strip()
        # crude delimiter identification
        if '\t' in line:
            delim = '\t'
        elif ',' in line:
            delim = ','
        else:
            print 'error: no recognised delimiter in header'
            return
        
        head = [x.strip() for x in line.split(delim)]
        
        try:
            colIndex = head.index(col)
        except ValueError as e:
            print 'error: column "%s" not found in header' % col
            return
        
        print >> d, line
        
        print 'extracting...'
        
        for line in s:
            if line.strip().split(delim)[colIndex].strip() == val:
                print >> d, line.strip()
    print 'done'
                
        
def printUsage():
    print 'Usage: extract.py src dst column value'

if __name__ == '__main__':
    if len(sys.argv) < 5:
        printUsage()
    else:
        extract(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

