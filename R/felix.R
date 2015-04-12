# functions implementing Felix's MARA (Scholkmann et al 2010)

# running SD
# margin is equivalent to the paper's k, ie window size = 2 * margin + 1
# we take somewhat ad hoc approach to the outside margins, assuming that
# they contain something resembling the inside margins, shuffled
running.func <- function ( x, margin=10, func=sd )
{
	pad.before <- sample(x[1:margin])
	pad.after <- sample(x[1:margin + length(x) - margin])
	supx <- c(pad.before, x, pad.after)
	result <- rep(0, length(x))
	for ( ii in 1:length(x) )
	{
		result[ii] <- func(supx[ii + 0:(2*margin)])
	}
	
	return(result)
}

# segmentation
# x is the running SD -- or other func, but note we assume non-negative
# returns a list of start indices, end indices, and whether each segment is "bad"
segment <- function ( x, threshold )
{
	thrx <- x > threshold
	end <- which(c(diff(thrx),1) != 0)
	start <- c(1, 1 + which(diff(thrx) != 0))[1:length(end)]
	bad <- !((1:length(end) + thrx[1]) %% 2)
	
	return ( list(start=start, end=end, bad=bad))
}

# spline fitting
# fit a spline to a single segment vector and subtract it
# returns a list of both components (ie, fitted baseline and remaining signal)
fit.bad.segment.natural <- function ( x, degree=ceiling(length(x)/2) )
{
	require(splines)
	tt <- 1:length(x)
	model <- lm( x ~ ns(tt, degree) )
	base <- predict(model, data.frame(tt=tt))
	return ( list(model=model, baseline=base, signal=x - base) )
}

# revised spline fitting using pspline library
# this should correspond better to Matlab csaps function
fit.bad.segment.pspline <- function ( x, p=0.01 )
{
	require(pspline)
	tt <- 1:length(x)
	model <- smooth.Pspline(tt, x, spar=(1-p)/p)
	base <- predict(model, tt)
	return ( list(model=model, baseline=base, signal=x - base) )
}

# LOESS fitting (replaces polynomial spline fitting in version 1.1 of MARA)
fit.bad.segment.loess <- function ( x, p=0.1 )
{
	tt <- 1:length(x)
	model <- loess(x ~ tt, data.frame(x=x, tt=tt), span=max(p, 1/length(x)))
	base <- predict(model)
	return ( list(model=model, baseline=base, signal=x - base) )
}

# offset segment x2 by a mean value determined from some portion of
# each segment according to the ad hoc rules in Table 1 of the paper
# returns the offset to be added to x2
determine.offset <- function ( x1, x2, hz=100, alpha=round(hz/3), beta=round(2*hz) )
{
	l1 <- length(x1)
	l2 <- length(x2)
	
	if ( l1 < alpha )
	{
		a <- mean(x1)
	}
	else if ( l1 < beta )
	{
		a <- mean(x1[(l1-alpha):l1])
	}
	else
	{
		theta1 <- ceiling(l1/10)
		a <- mean(x1[(l1-theta1):l1])
	}
	
	if ( l2 < alpha )
	{
		b <- mean(x2)
	}
	else if ( l2 < beta )
	{
		b <- mean(x2[1:alpha])		
	}
	else
	{
		theta2 <- ceiling(l2/10)
		b <- mean(x2[1:theta2])
	}
	
	return (a - b)
}

# apply Felix's MARA to a signal
# basing alpha and beta on the sampling frequency
# can use either spline fit function, but currently doesn't support non-default degree for the natural spline version
felix <- function ( x, margin, thresh, hz=100, p=0.1, func=sd, fit.type="loess", intermediates=TRUE )
{
	running <- running.func(x, margin, func)
	seg <- segment( running, thresh )
	
	pieces <- list()
	fits <- list()
	
	for ( ii in 1:length(seg$start) )
	{
		if ( seg$bad[ii] )
		{
			if ( fit.type=="pspline" )
			{
				fits[[ii]] <- fit.bad.segment.pspline(x[seg$start[ii]:seg$end[ii]], p)
			}
			else if ( fit.type=="natural" )
			{
				fits[[ii]] <- fit.bad.segment.natural(x[seg$start[ii]:seg$end[ii]])
			}
			else
			{
				fits[[ii]] <- fit.bad.segment.loess(x[seg$start[ii]:seg$end[ii]], p)				
			}
			pieces[[ii]] <- fits[[ii]]$signal
		}
		else
		{
			pieces[[ii]] <- x[seg$start[ii]:seg$end[ii]]
		}
	}
	
	shifted.pieces <- pieces
	
	offsets <- numeric(length(seg$start))
	for ( ii in 2:length(seg$start) )
	{
		offsets[ii] <- determine.offset(shifted.pieces[[ii-1]], shifted.pieces[[ii]], hz)
		shifted.pieces[[ii]] <- shifted.pieces[[ii]] + offsets[ii]
	}
	
	final <- unlist(shifted.pieces)
	
	if ( intermediates )
	{
		return ( list ( running=running, segments=seg, pieces=pieces, fits=fits, shifts=offsets, final=final ) )
	}

	return(final)
}

# simulate a NIRI signal matching the paper's sim description
sim.niri <- function ( n=5000,
					     hz=20,
					     f=c(1, 0.25, 0.1, 0.04),
					     mu=c(0.6, 0.2, 0.9, 1),
					     gamma=c(0.01, 0.01, 0.01, 0.05),
					     rescale=c(-1,1) )
{
	tt <- (1:n) / hz
	result <- numeric(n)
	
	# each component (by default there are four)
	# contributes a sinusioidal oscillation and Gaussian noise
	for ( ii in 1:length(f) )
	{
		result <- result + rnorm(n) * gamma[ii] + mu[ii] * sin(2 * pi *  f[ii] * tt)
	}
	
	if ( length(rescale)==2 )
	{
		result <- rescale[1] + (rescale[2] - rescale[1]) * (result - min(result)) / (max(result) - min(result))
	}
	
	return (result)
}

# simulate a baseline shift sequence similar to that described as MA1
sim.ma1 <- function ( n=5000, jumps=6, mu=0, dv=3 )
{
	result <- rep(rnorm(1, mu, dv),n)
	
	if ( jumps > 0 )
	{
		for ( ii in 1:jumps )
		{
			idx <- ceiling(runif(1, 1, n))
			if ( runif(1) < 0.5 )
			{
				result[1:idx] <- result[1:idx] + rnorm(1, mu, dv)
			}
			else
			{
				result[idx:n] <- result[idx:n] + rnorm(1, mu, dv)
			}
		}
	}
	return(result)
}

# simulate a noise spike sequence similar to that described as MA2
# the paper is not specific about this, but we will assume spikes are single sample duration
sim.ma2 <- function ( n=5000, spikes=6, mu=0, dv=5 )
{
	result <- rep(0, n)
	if ( spikes > 0 )
	{
		for ( ii in 1:spikes )
		{
			idx <- ceiling(runif(1,1,n))
			result[idx] <- rnorm(1, mu, dv)
		}
	}
	
	return(result)
}

# test the method with simulated data
# data, if supplied, should be the result of a previous call
# in which case the same signal etc are used, allowing testing with different parameter values
felix.test <- function ( margin=20, thresh=0.5, hz=20, p=0.1, n=5000, jumps=6, spikes=6, j.mu=0, j.dv=3, s.mu=0, s.dv=5, plot=TRUE, first.base="zero", data=NULL, fit.type="loess" )
{
	if ( is.null(data) )
	{
		signal <- sim.niri(n, hz)
		off <- sim.ma1(n, jumps, j.mu, j.dv) + sim.ma2(n, spikes, s.mu, s.dv)
	
		# this should help keep the plot more readable
		if ( first.base=="zero")
		{
			off <- off - off[1]
		}
		else if ( first.base=="centre" )
		{
			off <- off - mean(off)
		}
		
		combo <- signal + off
	}
	else
	{
		signal <- data$signal
		off <- data$off
		combo <- data$combo	
	}
	
	clean <- felix(combo, margin, thresh, hz, fit.type=fit.type)
	
	# compare original and cleaned signals
	rms <- rms(signal,clean$final)
	prd <- prd(signal,clean$final)
	r <- cor(signal, clean$final)
	
	if ( plot )
	{
		tt <- 1:n / hz
		plot ( combo ~ tt, type="l", col=3, xlab="Time (s)", ylab="Value", ylim=range(c(combo, off, clean$final), na.rm=TRUE) )
		lines( off ~ tt, col=4 )
		lines( signal ~ tt, col="grey")
		abline( v=which(diff(off) != 0)/hz, lty="dotted")
		lines( clean$final ~ tt, col=2 )
	}
	
	invisible ( list( signal=signal, off=off, combo=combo, clean=clean, rms=rms, prd=prd, r=r ) )
}

rms <- function ( x, y )
{
	return(sqrt(sum((x-y)^2)/length(x)))
}

prd <- function ( x, y )
{
	return(100 * sqrt(sum((x-y)^2)/sum(x^2)))
}


# wavelet-based alternative for multiscale outlier detection
mswdd <- function ( x, nlevels=6, alpha=1e-5 )
{
	require(wavethresh)
	N <- length(x)
	
	# once again, we're going to do some dubious padding at the boundaries
	# in this case, to a suitable power-of-two length (for the benefit of wd)
	newlen <- 2 ^ (1 + ceiling(log(N, base=2)))
	padlen <- (newlen - N)
	boundary <- min(50, floor(N/10))
	padbefore <- sample(x[1:boundary], ceiling(padlen/2), replace=TRUE)
	padafter <- sample(x[(N + 1 - boundary):N], floor(padlen/2), replace=TRUE)
	
	padded <- c(padbefore, x, padafter)
	
	# this is a stationary (aka a trous, maximum overlap, etc) Haar wavelet transform
	wav <- wd(padded, filter.number=1, family="DaubExPhase", type="station")
	
	# convert the wavelet coefficients into a matrix
	# (yes, we're currently doing unnecessary work here, out of laziness)
	nr <- wav$nlevels
	nc <- 2^nr
	vsg <- matrix(nrow=nr, ncol=nc)
	shift <- 1
	for ( ii in nr:1 )
	{
		vsg[ii,] <- accessD(wav, ii-1)[c((nc-shift+1):nc, 1:(nc-shift))]
		shift <- shift * 2
	}
	
	# cut down to size, discarding the padding columnes
	# plus any rows we don't care about
	vsg <- vsg[max(1, nr - nlevels + 1):nr, length(padbefore) + 1:N]
	
	# return same stuff as msddd below
	vout <- find.outliers.mat(vsg, alpha)
	idx2 <- colSums(vout)
	idx1 <- which(idx2 > 0)
	asr <- 100 * length(idx1)/N
	
	return (list(idx1=idx1, idx2=idx2, asr=asr, vsg=vsg, vout=vout))	
}

msddd <- function ( x, kmin=1, step=10, kmax=51, alpha=1e-5 )
{
	windows <- seq(kmin, kmax, step)
	vsg <- matrix(0, nrow=length(windows), ncol=length(x))
	
	for ( ii in 1:length(windows) )
	{
		vsg[ii,] <- running.func(x, windows[ii]) * running.func(x, windows[ii], mad)
	}
	
	vout <- find.outliers.mat(vsg, alpha)
	idx2 <- colSums(vout)
	idx1 <- which(idx2 > 0)
	asr <- 100 * length(idx1)/length(x)
	
	return (list(idx1=idx1, idx2=idx2, asr=asr, vsg=vsg, vout=vout))
}

find.outliers.mat <- function ( x, alpha=1e-5 )
{
	nr <- dim(x)[1]
	nc <- dim(x)[2]
	result <- matrix(0, nrow=nr, ncol=nc)
	for ( ii in 1:nr )
	{
		result[ii, find.outliers(x[ii,], alpha)] <- 1
	}
	return(result)
}

# return index of outliers, as determined by Thompson tau test
find.outliers <- function ( x, alpha=1e-5 )
{
	result <- NULL
	X <- x
	
	N <- length(X)
	tt <- tau(N, alpha)
	mr <- median(X)
	sr <- IQR(X)/1.349        # robust SD estimate according to author of Matlab function...
	
	mav <- max(abs(X - mr))
	
	while ( N>2 && mav > sr * tt )
	{
		result <- c(result, which(abs(x - mr) == mav))
		X <- X[which(abs(X-mr) < mav)]
		
		N <- length(X)
		tt <- tau(N, alpha)
		mr <- median(X)
		sr <- IQR(X)/1.349
		mav <- max(abs(X - mr))
	}
	
	return(result)
}

tau <- function ( N, alpha )
{
	tt <- qt(alpha/2, N-2)
	return ( -tt*(N-1)/(sqrt(N)*sqrt(N-2+tt^2)) )
}
