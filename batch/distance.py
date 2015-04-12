# custom distance functions for use with abc-sysbio
import numpy
import numpy.linalg

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
    return numpy.sqrt(numpy.sum((data1 - data2) * (data1 - data2)))

def cosine(data1, data2):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    if n != 0:
        c = numpy.clip(d/n, -1, 1)        # cosine similarity, in range [-1, 1]
        return (1 - c)/2                  # -> distance, in range [0, 1]
    else:
        return float('nan')

def angular(data1, data2):
    d = numpy.dot(data1, data2)
    n = numpy.linalg.norm(data1) * numpy.linalg.norm(data2)
    if n != 0:
        c = numpy.clip(d/n, -1, 1)        # cosine similarity, in range [-1, 1]
        return numpy.arccos(c)/numpy.pi   # -> angle, in range [0, 1]
    else:
        return float('nan')

def loglik(data1, data2, sigma=1):
    T = numpy.prod(data1.shape)
    return T/numpy.sqrt(2 * sigma * sigma * numpy.pi) - numpy.sum((data1 - data2) * (data1 - data2))/(2 * sigma * sigma)

def manhattan(data1, data2):
    return numpy.sum(numpy.fabs(data1 - data2))

def meandist(data1, data2):
    return numpy.sqrt(numpy.mean((data1 - data2) * (data1 - data2)))
