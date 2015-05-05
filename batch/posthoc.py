# posthoc signal transformations for model outputs being optimised
import numpy as np

def zero(x):
    return x - x[0]

def centre(x):
    return x - np.mean(x)

def norm(x):
    return (x - np.mean(x))/np.std(x)

def get(spec):
    if spec:
        if spec[0] == 'zero': return zero
        if spec[0] == 'centre': return centre
        if spec[0] == 'norm': return norm
        
        if spec[0] == 'offset':
            off = float(spec[1])
            return lambda x: x + off

        if spec[0] == 'scale':
            mult = float(spec[1])
            return lambda x: x * mult
        
        # maybe more of these later...

        # spec not recognised...
        return None
