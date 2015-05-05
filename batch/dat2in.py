#!/usr/bin/env python
# convert all DAT files in a directory to BCMD inputs

import os, os.path, sys
import subprocess

BATCH_DIR = os.path.dirname(os.path.abspath(__file__))
STEPS = os.path.join(BATCH_DIR, 'steps.py')
infiles = os.listdir(os.getcwd())

for src in infiles:
    if src.endswith('.dat'):
        dst, dummy = os.path.splitext(src)
        dst += '.input'
        print '* converting %s' % src
        with open(dst, 'w') as f:
            subprocess.call(['python', STEPS, src], stdout=f)
