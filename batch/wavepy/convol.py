#! /usr/bin/env python

import sys
import numpy as np

def convfft(a,b):
    len_c = len(a)+len(b)-1
    a=np.array(a)
    b=np.array(b)
    az=np.zeros(len_c-len(a))
    bz=np.zeros(len_c-len(b))
    a=np.append(a,az)
    b=np.append(b,bz)
    
    x=np.fft.fft(a)
    y=np.fft.fft(b)
    z=x*y
    oup=np.fft.ifft(z)
    return oup
    

def convol(a,b):
    len_c = len(a)+len(b)-1
    a=np.array(a)
    b=np.array(b)
    az=np.zeros(len_c-len(a))
    bz=np.zeros(len_c-len(b))
    a=np.append(a,az)
    b=np.append(b,bz)
    c=np.zeros(len_c)
    
    for i in range(len_c):
        for j in range(i+1):
            oup=a[j]*b[i-j]
            c[i]+=oup
            
    return c        



    
    