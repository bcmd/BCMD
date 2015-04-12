#! /usr/bin/env python

import sys
import numpy as np
from math import ceil

def upsamp(inp,M):
    x = np.array(inp)
    M=int(M)
    N = M * len(x)
    y=[]
    
    for i in range(N):
        if i%M == 0:
            y.append(x[i/M])
        else:
            y.append(0.0)
    
    return y


def downsamp(inp,M):
    x=np.array(inp)
    N = int(ceil(len(x) *1.0 / M))
    y=[]
    
    for i in range(N):
        y.append(x[i*M])
    
    return y
            