# assorted data cleaning utilities

# wavelet denoising functions
require(wavethresh)

# interpolate missing data
fill <- function (x)
{
	start.val <- NA
	end.val <- NA
	
	from <- 1
	
	while ( TRUE )
	{	
		while ( from <= length(x) && !is.na(x[from]) )
		{
			from <- from + 1
		}
	
		if ( from > length(x) )
		{
			return(x)
		}
		
		if ( from > 1 )
		{
			start.val <- x[from - 1]
		}
		
		to <- from + 1
		
		while ( to <= length(x) && is.na(x[to]) )
		{
			to <- to + 1
		}
		
		if ( to <= length(x) )
		{
			end.val <- x[to]
		}
		else
		{
			end.val <- start.val
			if ( is.na(end.val) )
			{
				# give up -- whole vector is NA
				return(x)
			}
			to <- length(x)
		}
		
		if ( is.na(start.val) )
		{
			start.val <- end.val
		}
		
		for ( ii in from:to )
		{
			x[ii] = start.val + (ii-from + 1) * (end.val - start.val) / (to - from + 1)
		}
		
		from <- to
	}
}

# pad a vector with NAs so that its length is a power of two
pad.pow2 <- function ( x, include.lengths=FALSE )
{
	padlen <- 2^ceiling(log(length(x),2)) - length(x)
	
	if ( padlen != 0 )
	{
		before <- rep(NA, floor(padlen/2))
		after <- rep(NA, ceiling(padlen/2))
		
		if ( include.lengths )
		{
			return(list(x=c(before, x, after), before=floor(padlen/2), after=ceiling(padlen/2)))
		}
		
		return ( c(before, x, after) )
	}
	
	if ( include.lengths )
	{
		return(list(x=x, before=0, after=0))
	}
	
	return(x)
}

# basic wavelet denoising
# default settings give moderate smoothing but won't do much about
# highly quantized signals like the CYRIL SpO2 values
# -- for these, try:
#   ... by.level=TRUE, family="DaubExPhase", filter.number=10
wden <- function ( x,
				   policy="sure",
				   av.basis=FALSE,
				   level=0,
				   family="DaubLeAsymm",
				   filter.number=10,
				   ... )
{
	xp <- pad.pow2(x, TRUE)
	xf <- fill(xp$x)
	
	w <- wd(xf, type="station", family=family, filter.number=filter.number )
	
	# this is a dubious rule of thumb based on a few feeble tests
	if ( is.na(level) )
	{
		level <- max(0, nlevelsWT(w)-12)
	}
	
	wth <- threshold(w, policy="sure", levels=level:(nlevelsWT(w)-1), ...)
	
	# convert to packet ordering
	st <- convert(wth)
	
	if ( av.basis )
	{
		# invert transform with average basis
		iw <- AvBasis(st)
	}
	else
	{
		# invert transform with Coifman-Wickerhauser basis
		iw <- InvBasis(st, MaNoVe(st))
	}
	
	return(iw[xp$before + 1:length(x)])
}

# align to some initial baseline segment
zero <- function ( x, seg=500, fun=median )
{
	return(x - fun(x[1:seg]))
}

# scale to some normalising metric
rescale <- function ( x, fun=sd )
{
	return(x/fun(x))
}

# normalise via the above
normalise <- function ( x, seg=500, zerofun=median, scalefun=sd )
{
	return(rescale(zero(x, seg, zerofun), scalefun))
}

# moving function filter
moving <- function ( x, window=50, fun=median )
{
	result <- rep(NA, length(x))
	for ( ii in 1:length(x) )
	{
		result[ii] <- fun(x[max(1,ii-floor(window/2)):min(length(x),ii+ceiling(window/2))])
	}
	return(result)
}

# first order filter in discrete (EWMA) form
ewma <- function ( x, tau, tt=1, x0=NULL )
{
	rr <- x
	
	if ( ! is.null(x0) )
	{
		rr[1] <- (tau * x0 + tt * x[1])/(tau + tt)
	}
	
	if ( length(x) > 1 )
	{
		for ( ii in 2:length(x) )
		{
			rr[ii] <- (tau * rr[ii-1] + tt * x[ii])/(tau + tt)
		}
	}
	
	return(rr)
}

# moving window linear regression
# returns a matrix of coefficients (rows=time points, cols=coefs)
# and a vector of corresponding R^2 values
mwlm <- function ( formula, data, window, step=1 )
{
	nr <- dim(data)[1]
	wins <- floor((nr - window + 1)/step)
	
	coefs <- NULL
	Rsq <- NULL
	
	for ( ii in 0:(wins-1) )
	{
		lmx <- lm(formula, data[ii * step + 1:window,])
		coefs <- rbind(coefs, lmx$coefficients)
		Rsq <- c(Rsq, summary(lmx)$r.squared)
	}
	
	return(list(coefs=coefs, r.squared=Rsq))
}
