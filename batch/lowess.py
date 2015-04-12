# adaptation of the lowess function from BioPython to work in isolation
import numpy as np
import numpy.random as rng

def lowess(x, y, f=2. / 3., iter=3):
    n = len(x)
    r = int(np.ceil(f * n))
    h = [np.sort(abs(x - x[ii]))[r] for ii in xrange(n)]
    w = np.clip(abs(([x] - np.transpose([x])) / h), 0.0, 1.0)
    w = 1 - w * w * w
    w = w * w * w
    yest = np.zeros(n)
    delta = np.ones(n)
    for iteration in xrange(iter):
        for ii in xrange(n):
            weights = delta * w[:, ii]
            weights_mul_x = weights * x
            b1 = np.dot(weights, y)
            b2 = np.dot(weights_mul_x, y)
            A11 = sum(weights)
            A12 = sum(weights_mul_x)
            A21 = A12
            A22 = np.dot(weights_mul_x, x)
            determinant = A11 * A22 - A12 * A21
            beta1 = (A22 * b1 - A12 * b2) / determinant
            beta2 = (A11 * b2 - A21 * b1) / determinant
            yest[ii] = beta1 + beta2 * x[ii]
        residuals = y - yest
        s = np.median(abs(residuals))
        delta[:] = np.clip(residuals / (6 * s), -1, 1)
        delta[:] = 1 - delta * delta
        delta[:] = delta * delta
    return yest

# simple test driver
if __name__ == "__main__":
    x = np.linspace(0, 2 * np.pi)
    y = 5 * np.sin(x)
    ny = y + rng.randn(len(y))
    ly = lowess(x, ny, f=0.3, iter=5)
    print 'x\ty\tny\tly'
    for ii in range(len(x)):
        print '%f\t%f\t%f\t%f' % (x[ii], y[ii], ny[ii], ly[ii])
