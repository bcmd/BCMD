#!/usr/bin/env python

# module implementing Felix's artefact removal method, based on the earlier R version

import sys, os, os.path
import numpy as np
import scipy as sp
import numpy.random as rng
import scipy.interpolate as spi
import scipy.stats as sst
import scipy.signal as sig

# for the moment, we keep these locally rather than requiring separate installation
import wavepy as wv
import lowess

# our signal generator module
import siggen

# calculate a running function of some data -- SD by default
# currently uses a shuffled-extension policy for boundaries, may add other options later
def running ( x, margin=10, func=np.std ):
    before = x[range(margin)]
    after = x[range(len(x) - margin, len(x))]
    rng.shuffle(before)
    rng.shuffle(after)
    padded = np.concatenate((before,x,after))
    
    result = np.zeros(len(x))
    for ii in range(len(x)):
        result[ii] = func(padded[range(ii, ii + 2 * margin + 1)])
    
    return result

# segment a data array (assumed non-negative) based on a simple threshold
# main use case is that x is the output of running(), above, but this is not required
# TODO: allow elimination of small intervals
def segment ( x, threshold ):
    thrx = x > threshold
    ends = np.where(np.concatenate((np.diff(thrx), np.array([1]))))[0]
    starts = np.concatenate((np.array([0]), 1 + ends[range(len(ends) - 1)]))
    bad = thrx[starts]
    
    return { 'start':starts, 'end':ends, 'bad':bad }

# fit a cubic smoothing spline to a (bad) data segment and subtract it
# smoothness is essentially the mean SSE of the resulting fit
# (ie, we scale by len(x) for the call to UnivariateSpline)
# this relates in some unhelpful way to the p parameter in Matlab's csaps equivalent
# (as used in the original implementation) -- so a sensible default will need to be empirically determined...
def fit_spline ( x, t=None, smoothness=None ):
    if smoothness is None:
        smoothness = 0.02 * np.std(x)
    if t is None:
        t = np.linspace(0,1,len(x))
    model = spi.UnivariateSpline(t, x, s=smoothness * len(x))
    base = model(t)
    return { 'model':model, 'baseline':base, 'signal': x - base, 't':t }

# fit a lowess (1st order) local smoothing spline, with broadly the same
# consequences as above, but no model is returned (lowess currently doesn't create one)
# span is the smoothing span, in (0, 1], controlling the smoothness
# iter is the number of robustness iterations -- higher may be less biased, but slower
def fit_lowess ( x, t=None, span=0.3, iter=4 ):
    if t is None:
        t = np.linspace(0,1,len(x))
    base = lowess.lowess(t, x, f=span, iter=iter)
    return { 'baseline':base, 'signal': x - base, 't':t }

# calculate offset for a segment wrt to the previous one by a mean value determined
# from some portion of each according to the ad hoc rules in Table 1 of the paper
def find_offset ( x1, x2, hz=20, alpha=None, beta=None ):
    if alpha is None:
        alpha = np.round(hz/3)
    if beta is None:
        beta = np.round(hz * 2)
    
    l1 = len(x1)
    if l1 < alpha:
        a = np.mean(x1)
    elif l1 < beta:
        a = np.mean(x1[(-alpha):])
    else:
        theta1 = np.ceil(l1/10)
        a = np.mean(x1[(-theta1):])
    
    l2 = len(x2)
    if l2 < alpha:
        b = np.mean(x2)
    elif l2 < beta:
        b = np.mean(x2[:alpha])
    else:
        theta2 = np.ceil(l2/10)
        b = np.mean(x2[:theta2])
    
    return a-b

# combined artefact removal algorithm
def mara ( x, margin, thresh, hz=20, smoothness=None, func=np.std, alpha=None, beta=None, intermediates=True ):
    criterion = running(x, margin, func)
    segs = segment(criterion, thresh)
    nn = len(segs['start'])
    pieces = [None] * nn
    fits = [None] * nn
    
    for ii in range(len(segs['start'])):
        if segs['bad'][ii]:
            fits[ii] = fit_spline(x[segs['start'][ii]:(segs['end'][ii]+1)], smoothness=smoothness)
            pieces[ii] = fits[ii]['signal']
        else:
            pieces[ii] = x[segs['start'][ii]:(segs['end'][ii]+1)]
    
    offsets = [0] * nn
    for ii in range(1, nn):
        offsets[ii] = find_offset ( pieces[ii-1], pieces[ii], hz, alpha, beta )
        pieces[ii] = pieces[ii] + offsets[ii]
    
    final = np.concatenate(pieces)
    
    if intermediates:
        return { 'criterion' : criterion,
                 'segments' : seg,
                 'pieces' : pieces,
                 'fits' : fits,
                 'shifts' : offsets,
                 'final' : final }
    else:
        return final

# simulate a NIRI signal as a mixture of sinusoidal and noise componente
# defaults are as described in the paper
# f is frequency in Hz, mu is component amplitude, gamma is gaussian noise sd
# phi is an optional phase shift, lo & hi specify rescaling
def niri ( n=5000,
           hz=20,
           f=[1, 0.25, 0.1, 0.04],
           mu=[0.6, 0.2, 0.9, 1],
           gamma=[0.01, 0.01, 0.01, 0.05],
           phi=[0, 0, 0, 0],
           lo=-1,
           hi=1 ):
    tt = 2 * np.pi * np.array(range(n), dtype=np.float32)/hz
    result = np.zeros(n)
    
    for ii in range(len(f)):
        result += mu[ii] * np.sin(f[ii] * tt) + gamma[ii] * rng.randn(n)
    
    return siggen.rescale(result, lo, hi)

# simulate a baseline shift sequence similar to that termed MA1 in the paper
def ma1 ( n=5000, jumps=6, mu=0, dv=3 ):
    result = np.zeros(n)
    for ii in range(jumps):
        idx = np.floor(rng.rand(1)[0] * n)
        off = rng.randn(1)[0] * dv + mu
        if rng.rand(1)[0] < 0.5:
            result[:idx] += off
        else:
            result[idx:] += off
    return result

# simulate a spike sequence similar to that termed MA2 in the paper
def ma2 ( n=5000, spikes=6, mu=0, dv=5 ):
    result = np.zeros(n)
    for ii in range(spikes):
        idx = np.floor(rng.rand(1)[0] * n)
        result[idx] = rng.randn(1)[0] * dv + mu
    return result

# stats used in the paper for comparing recovered sequence to known original
def stats ( actual, recovered ):
    rms = np.sqrt(np.mean((actual-recovered)**2))
    prd = 100 * np.sqrt(np.sum((actual-recovered)**2)/len(actual))
    r, p = sst.pearsonr(actual, recovered)
    return { 'rms': rms, 'prd': prd, 'r': r, 'p': p }


# test with simulated data
def test ( margin=15, thresh=0.5, hz=20, smth=None, n=5000, jumps=6, spikes=6,
           j_mu=0, j_dv=3, s_mu=0, s_dv=5, first_base='zero', data=None, intermediates=False ):
    if data is None:
        signal = niri ( n, hz )
        off = ma1( n, jumps, j_mu, j_dv ) + ma2( n, spikes, s_mu, s_dv )
        
        if first_base == 'zero':
            off = off - off[0]
        elif first_base == 'centre':
            off = off - np.mean(off)
        
        combo = signal + off
    else:
        signal = data['signal']
        off = data['off']
        combo = data['combo']
    
    clean = mara( combo, margin, thresh, hz, smth, intermediates=intermediates )
    
    if intermediates:
        st = stats( signal, clean['final'] )
    else:
        st = stats( signal, clean )

    return { 'signal': signal, 'off': off, 'combo': combo, 'clean': clean,  'stats': st }

# Felix's slightly dubious dispersion measure -- product of std dev and MAD (why?)
def std_mad ( x ):
    return np.std(x) * mad(x)

# median absolute deviation
# why this isn't defined in SciPy be default I have no idea
# here we define only for a 1d array
# default scale factor taken from R -- this may not match the Matlab original
def mad ( x, scale=1.4826 ):
    return scale * np.median(np.abs(x - np.median(x)))

# Felix's multiscale SD discontinuity detection
def msddd ( x, alpha=1e-5, kmin=1, kmax=52, step=10 ):
    wins = range(kmin, kmax, step)
    vsg = np.zeros((len(wins), len(x)))
    for ii in range(len(wins)):
        vsg[ii,] = running(x, margin=wins[ii], func=std_mad)
    
    return discontinuities(vsg, alpha)

# Matt's wavelet-based discontinuity detection
def mswdd ( x, alpha=1e-5, nlevels=6, boundary=100, prop=0.1 ):
    # pad to the next power of two in size
    N = len(x)
    maxlevs = np.ceil(np.log2(N))
    newlen = 2 ** (1 + maxlevs)
    padlen = newlen - N
    boundary = np.min((boundary, np.floor(prop * N)))
    padbefore = rng.choice(x[0:boundary], np.ceil(padlen/2))
    padafter = rng.choice(x[(N-boundary+1):N], np.floor(padlen/2))
    padded = np.concatenate((padbefore, x, padafter))
    
    # get wavelet transform
    J = np.min((nlevels + 1, maxlevs + 1))
    vsg = wv.dwt.swt(padded, J, 'db1')[0].reshape(vsg, (J, newlen))

    # shift rows to align the scale levels
    shift = newlen/2
    for ii in range(1, vsg.shape[0]):
        idx = range(newlen - shift, newlen)
        idx.extend(range(newlen - shift))
        vsg[ii,] = vsg[ii, idx]
        shift = shift/2
    
    # drop 1st (DC) row and padding
    vsg = vsg[1:,len(padbefore):(len(padbefore)+N)]
    
    return discontinuities(vsg, alpha)

# shared outlier-based discontinuity detection
def discontinuities ( vsg, alpha=1e-5 ):
    nr, nc = vsg.shape
    vout = np.zeros((nr, nc))
    
    for ii in range(nr):
        vout[ii, find_outliers(vsg[ii,], alpha)] = 1
    
    idx2 = np.sum(vout, 0)
    idx1 = np.flatnonzero(idx2)
    asr = 100 * float(len(idx1))/nc
    
    return { 'vsg':vsg, 'vout':vout, 'idx1':idx1, 'idx2':idx2, 'asr':asr }

# return index of outliers in a data set, as determined by a Thompson tau test
def find_outliers ( x, alpha=1e-5 ):
    result = []
    X = x.copy()
    
    mr = np.median(X)
    q23 = np.percentile(X, [25, 75])
    sr = (q23[1] - q23[0]) / 1.349
    
    val = np.max(np.abs(X - mr))
    
    while len(X) > 2 and val > sr * tau(len(X), alpha):
        # indices of outlier value in original array
        result.extend(np.flatnonzero(np.abs(x - mr) == val))
        
        # remove outliers from working array
        X = X[np.flatnonzero(np.flatnonzero(np.abs(X - mr) < val))]

        # rinse and repeat
        mr = np.median(X)
        q23 = np.percentile(X, [25, 75])
        sr = (q23[1] - q23[0]) / 1.349
    
    return result

# test value for the Thompson outlier test
# N is the data count, alpha the significance level
def tau ( N, alpha=1e-5 ):
    t = sst.t.ppf(alpha/2, N-2)
    return t * (1 - N) / (np.sqrt(N) * sqrt(N - 2 + t * t))

# command-line invocation -- currently runs test with all defaults
# dumping results to stdout as tab-delim text, stats to stderr
if __name__ == '__main__':
    tt = test()
    print >> sys.stderr, 'Recovered signal statistics'
    print >> sys.stderr, 'RMSE: %g' % tt['stats']['rms']
    print >> sys.stderr, 'PRD: %g%%' % tt['stats']['prd']
    print >> sys.stderr, 'r: %g' % tt['stats']['r']
    
    print 'signal\toffset\tcombo\tclean'
    for ii in range(len(tt['signal'])):
        print '%g\t%g\t%g\t%g' % ( tt['signal'][ii], tt['off'][ii], tt['combo'][ii], tt['clean'][ii] )



    
