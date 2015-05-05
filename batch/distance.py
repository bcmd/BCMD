# custom distance functions for use with abc-sysbio and the BCMD batch scripts
import numpy
import numpy.linalg

# how do we deal with non-numeric results?
# in some cases, client code may want to change this in order to get
# wrong but pragmatic results (yes, this is a hack)
SUBSTITUTE = numpy.nan

# convert non-finite results to a consistent value
def substitute(x):
    if numpy.isfinite(x):
        return x
    return SUBSTITUTE

# -- ABC-SYSBIO interface versions, which wrap the return value in a list

# Euclidean distance
def euclideanDistance(data1, data2, parameters, model):
    return [numpy.sqrt(numpy.sum((data1 - data2) * (data1 - data2)))]

# Tracy's custom distance metric
def meanDistance(data1, data2, parameters, model):
    return [numpy.sqrt(numpy.mean((data1 - data2) * (data1 - data2)))]

# simple Manhattan/L1 distance
def manhattanDistance(data1, data2, parameters, model):
    return [numpy.sum(numpy.fabs(data1 - data2))]

# log-likelihood distance metric for noise ~ N(0, sigma^2)
# this is probably functionally equivalent to the Euclidean distance
# (though it scales differently)
# note that the ASB interface does not allow for passing noise, so
# we create a function with sigma baked in
def loglikDistanceFunc(sigma=1):
    def loglikDistance(data1, data2, parameters, model):
        T = numpy.prod(data1.shape)
        return [ T/numpy.sqrt(2 * sigma * sigma * numpy.pi)
                 - numpy.sum((data1 - data2) * (data1 - data2))/(2 * sigma * sigma) ]
    return loglikDistance

# angular distance between 2 data vectors
# this is basically a correlation coefficient, which aims to capture similarity of shape
# it should be independent of offset and scale, but is probably pretty sensitive to noise
# scaled to the interval [0,1], where 0 is perfect alignment
def angularDistance(data1, data2, parameters, model):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    c = d/n
    return [numpy.arccos(c)/numpy.pi]
    
# similar to the above, but without conversion to an angle
# again, scaled to the interval [0,1]
def cosineDistance(data1, data2, parameters, model):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    c = d/n
    return [(1 - c)/2]


# -- generic distance functions that just return a scalar

def euclidean(data1, data2):
    return substitute(numpy.sqrt(numpy.sum((data1 - data2) * (data1 - data2))))

def cosine(data1, data2):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    if n != 0:
        c = numpy.clip(d/n, -1, 1)        # cosine similarity, in range [-1, 1]
        return substitute((1 - c)/2)      # -> distance, in range [0, 1]
    else:
        return SUBSTITUTE

def angular(data1, data2):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    if n != 0:
        c = numpy.clip(d/n, -1, 1)                    # cosine similarity, in range [-1, 1]
        return substitute(numpy.arccos(c)/numpy.pi)   # -> angle, in range [0, 1]
    else:
        return SUBSTITUTE

# estimate negative log likelihood of the difference between the data sets arising
# from gaussian noise with mean zero and the given standard deviation
# if the latter is not supplied, the sample standard deviation is used (this may be stupidly self-fulfilling)
# if this distance is minimised, then the Hessian at the optimum gives an estimate as to the
# parameter uncertainty, albeit under incredibly dubious distributional assumptions...
def loglik(data1, data2, sigma=None):
    resid = data1 - data2
    T = numpy.prod(data1.shape)
    if sigma is None:
        sigma = numpy.std(resid)
    return substitute(T * numpy.log(2 * numpy.pi * sigma * sigma)/2 + numpy.sum(resid * resid)/(2 * sigma * sigma))

# specialise loglik with an explicit sigma
def loglikWithSigma(sigma):
    def f (data1, data2):
        return loglik(data1, data2, sigma)
    return f

def manhattan(data1, data2):
    return substitute(numpy.sum(numpy.fabs(data1 - data2)))

def meandist(data1, data2):
    return substitute(numpy.sqrt(numpy.mean((data1 - data2) * (data1 - data2))))
