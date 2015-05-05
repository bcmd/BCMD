# quick hack script to run a bunch of morris sensitivity tests
# using all the new hypercapnia inputs in turn

import os, os.path, sys
import subprocess

datafiles = os.listdir('scratch/hx')
for df in datafiles:
    if df.endswith('.csv'):
        print '* running dsim with model B1M2, outputs Vmca and CCO, input ' + df
        subprocess.call(['/usr/bin/env', 'python', 'dsim.py', 'B1M2.dsimjob', 'scratch/hx/' + df])

# it's marginally more convenient for postprocessing to have dirs with same output consecutive,
# so loop a second time rather than calling inside the above
for df in datafiles:
    if df.endswith('.csv'):
        print '* running dsim with model BS, outputs Vmca and CCO, input ' + df
        subprocess.call(['/usr/bin/env', 'python', 'dsim.py', 'BS.dsimjob', 'scratch/hx/' + df])

