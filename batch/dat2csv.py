#!/usr/bin/env python

# simple script to read experiment data from .DAT input files
# and write it out as a CSV

import sys, os, os.path
import csv

import steps

def dat2csv(name):
    print 'attempting to read %s' % name
    content = steps.readBraincirc(name)
    ts = content.get('data', False)
    
    if ts:
        headers = content['header']['chosen_param']
        if 'time_step' not in content['header']:
            headers = ['t'] + headers
        base, ext = os.path.splitext(name)
        
        print 'attempting to write %s.csv' % base
        with open(base + '.csv', 'wb') as file:
            writer = csv.writer(file, quoting = csv.QUOTE_NONNUMERIC)
            writer.writerow(headers)
            writer.writerows(ts)
    else:
        print 'time series data not found'
    

if __name__ == '__main__':
    for name in sys.argv[1:]:
        if name.lower().endswith('.dat'):
            try:
                dat2csv(name)
            except Exception as e:
                print e
