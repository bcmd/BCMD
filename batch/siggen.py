#! /usr/bin/env python
import sys, os
import scipy as sp
import numpy as np
import scipy.signal as sig
import numpy.random as rng

# rescale a numpy array into the given range
def rescale ( vv, lo=0, hi=1, **kwargs ):
    # may want to skip rescaling in some cases
    if lo is None or hi is None:
        return vv
    
    mn = np.min(vv)
    mx = np.max(vv)
    return lo + ( vv - mn ) * ( hi - lo ) / ( mx - mn )

# unified interface for generating a single test waveform at specified time points
def wave ( tt, lo=0, hi=1, freq=0.1, phi=0, kind='saw', **kwargs ):

    # periodic signal functions have defined period 2 * pi, so we
    # scale the time points accordingly
    sct = tt * freq * 2 * np.pi + phi
    
    if kind == 'saw':
        if kwargs is not None and 'width' in kwargs:
            ss = sig.sawtooth ( sct, width=kwargs['width'] )
        else:
            ss = sig.sawtooth ( sct )
    elif kind == 'square':
        if kwargs is not None and 'duty' in kwargs:
            ss = sig.square ( sct, duty=kwargs['duty'] )
        else:
            ss = sig.square ( sct )
    elif kind == 'sine':
        ss = np.sin ( sct )
    
    elif kind == 'uniform':
        ss = rng.rand(len(tt))
    elif kind == 'gaussian':
        ss = rng.randn(len(tt))
        if kwargs is not None:
            ss = ss * kwargs.get('sd', 1) + kwargs.get('mean', 0)
    elif kind == 'walk':
        ss = rng.randn(len(tt))
        if kwargs is not None:
            ss = ss * kwargs.get('sd', 1) + kwargs.get('mean', 0)
        ss = np.cumsum(ss)
    
    # potentially other kinds here
    
    # default to a constant 0 output
    else:
        return tt * 0
    
    return rescale(ss, lo, hi)


# generate a signal that's the sum of multiple component waves at given timepoints
def waves ( tt, specs=[ { 'kind': 'saw', 'width': 1 } ] ):
    result = 0
    for spec in specs:
        if spec['kind'] == 'rescale':
            result = rescale(result, **spec)
        else:
            result = result + wave ( tt, **spec )
    return result

    
# as above, but constructing the times vector and optionally rescaling the final wave
def generate ( n=20, timescale=1, start=0, lo=0, hi=1, specs=[ { 'kind': 'saw', 'width': 1 } ] ):
    tt = np.linspace( start=start, stop=start + (n-1) * timescale, num=n )
    result = waves(tt, specs)
    return { 't' : tt, 'signal' : rescale(result, lo, hi) }
    
    
if __name__ == '__main__':
    # simple test driver -- redirect to file to examine
    sp1 = { 'kind':'sine', 'lo':-10, 'hi':10, 'freq':10 }
    sp2 = { 'kind':'walk', 'sd':0.1, 'lo':None }
    sp3 = { 'kind':'square', 'lo':0, 'hi':10, 'freq':3 }
    sp4 = { 'kind':'gaussian', 'sd':0.5, 'lo':None }
    wv = generate ( n=1000, timescale=0.001, specs=[ sp1, sp2, sp4 ], lo=0, hi=5 )
    print 't\tsignal'
    for ii in range(len(wv['t'])):
        print '%g\t%g' % (wv['t'][ii], wv['signal'][ii])