# quick hack script to run a big bunch of simulated data files through BrainSignals

import os, os.path, sys
import subprocess

IN_DIR = '../data/bs_sim/worse_in'
OUT_DIR = '../data/bs_sim/worse_out'
MODEL = '../build/bsrf_BS.model'

infiles = os.listdir(IN_DIR)

for src in infiles:
    if src.endswith('.input'):
        dst, dummy = os.path.splitext(src)
        dst += '.out'
        print '* running %s with input %s' % (MODEL, src)
        subprocess.call([MODEL, '-i', os.path.join(IN_DIR, src), '-o', os.path.join(OUT_DIR, dst)])

