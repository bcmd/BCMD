# quick hack script to run a big bunch of simulated data files through BrainSignals

import os, os.path, sys
import subprocess

IN_DIR = '../../text/tracy/files/bcmd'
OUT_DIR = '../../text/tracy/files/bcmd_out'
MODEL = '../build/brainpiglet2-0.model'

infiles = os.listdir(IN_DIR)

for src in infiles:
    if src.endswith('.input'):
        dst, dummy = os.path.splitext(src)
        dst += '.out'
        print '* running %s with input %s' % (MODEL, src)
        subprocess.call([MODEL, '-i', os.path.join(IN_DIR, src), '-o', os.path.join(OUT_DIR, dst)])

