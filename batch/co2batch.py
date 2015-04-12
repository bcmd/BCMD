# quick hack script to run a bunch of morris sensitivity tests
# using all the co2 inputs in turn

import os, os.path, sys
import subprocess

datafiles = os.listdir('scratch/co2')
for df in datafiles:
    if df.endswith('.dat'):
        print '* running dsim with input ' + df
        subprocess.call(['/usr/bin/env', 'python', 'dsim.py', 'funcact3.dsimjob', 'scratch/co2/' + df])
