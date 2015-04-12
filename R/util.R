# data analysis utility functions for batch BCMD model outputs
# (sensitivity analysis, perhaps ABC?)

# this is a bit of a scratchpad at the moment
# at some point these things may migrate to Python...

# rescale a vector into range [0,1]
normalise <- function ( x )
{
	return ( (x - min(x))/(max(x) - min(x)) )
}

# a light colour palette for our heatmaps
# -- lowest value is white for cleaner appearance on posters etc
pallid <- function ( n=100,
					 min.r=0.99, gamma.r=0.5,
					 min.g=0.6, gamma.g=1,
					 min.b=0.6, gamma.b=0.5 )
{
	ii <- ((n-1):0) / (n-1)
	rr <- min.r + (1-min.r) * ii ^ gamma.r
	gg <- min.g + (1-min.g) * ii ^ gamma.g
	bb <- min.b + (1-min.b) * ii ^ gamma.b
	
	return ( rgb(rr, gg, bb) )	
}

# function to plot a sensitivity heat map from aggregated batch job data
# by default, it reads the data from a file, though if you're doing this
# a lot it makes sense to load it once and pass it in via the dat parameter
heat_cross <- function ( dat=read.table("aggregate.txt", header=TRUE),

                         # distance column to graph
                         field="dist_L1_mu_star",
                         
                         # select on species -- default picks the first one as ordered by unique()
                         #  -- which will likely be the first in the file
                         species=NULL,                
                                                      
                         # whether to scale all values into range [0,1]
                         norm=TRUE,
                         
                         # data column to use for rows in plot
                         row="input",
                         
                         # data column to use for columns in plot
                         col="Param",
                         
                         # actually do the plotting? pass false if you just want to
                         # get back the data
                         plot=TRUE,
                         
                         # colours to plot with -- a colour vector, as returned by standard
                         # R funcs like rainbow() or heat.colors()
                         # -- higher entries are used for bigger distance results
                         clut=pallid(),
                         
                         # the next lot of entries specify colours for the summary overlay
                         over.col.max.fill="gray90",
                         over.col.max.pt="gray30",
                         over.col.max.line="gray40",
                         over.col.mean.pt="gray20",
                         over.col.mean.line="gray10",
                         
                         # rescale the overlay by some amount (usually to keep the arrows inside the plot)
                         over.rescale=0.975,
                         
                         # fill colour for marking params whose effect is identically zero
                         empty.col="white",
                         
                         # colour for the label text
                         label.col="darkblue",
                         
                         # value at which labels start getting plotted
                         # (probably only makes sense if normalising)
                         label.thresh=0.25,
                         
                         # label offset from arrowhead position
                         label.pos=4,
                         
                         # draw border around plot
                         border=TRUE,
                         
                         # leave out all parameters with zero effect
                         omit.empty=FALSE,
                         
                         # axis labels
                         xlab="Parameter",
                         ylab="Input File",
                         
                         # main title
                         main="L1 mu*",
                         
                         # append species to title in parentheses?
                         insert.species=TRUE,
                         
                         # return a list including some intermediate calculated values
                         # as well as the data itself
                         intermediates=TRUE,
                         
                         # apply a gamma correction to the distance values
                         # -- useful to improve visibility if the distribution is very skewed
                         # (probably only makes sense if normalising)
                         gamma=1,
                         
                         # other values to pass through to plotting functions
                         # note that using this may throw up all kinds of warnings
                         ... )
{
	if ( is.null(species)
		 && row != "Species"
		 && col != "Species"
		 && length(unique(dat$Species)) > 1 )
	{
		species <- unique(dat$Species)[1]
	}
	
	if ( ! is.null(species))
	{
		dat <- dat[dat$Species==species,]
		if ( insert.species )
		{
			main <- paste(main, " (", species, ")", sep="" )
		}
	}
	
	row_levels <- levels(dat[[row]])
	col_levels <- levels(dat[[col]])
	
	result <- matrix(nrow=length(row_levels), ncol=length(col_levels))
	rownames(result) <- row_levels
	colnames(result) <- col_levels
	
	if ( norm )
	{
		val <- normalise(dat[[field]])
	}
	else
	{
		val <- dat[[field]]
	}
	
	# optional gamma correction to scale values for visibility
	val <- val^gamma
	
	for ( rr in 1:length(row_levels) )
	{
		for ( cc in 1:length(col_levels) )
		{
			result[rr,cc] <- val[dat[[row]]==row_levels[rr] & dat[[col]]==col_levels[cc]]
		}
	}
	
	maxes <- apply(result, 2, max)
	means <- apply(result, 2, mean)
	
	if ( omit.empty )
	{
		result <- result[, maxes != 0]
		means <- means[maxes != 0]
		col_levels <- col_levels[maxes != 0]
		maxes <- maxes[maxes != 0]	
	}
	
	x <- 0:(length(maxes)-1)/(length(maxes)-1)
	
	if ( plot )
	{
		suppressWarnings(image(t(result), main=main, xlab=xlab, ylab=ylab, col=clut, axes=border, tick=FALSE, labels=FALSE, ...))
		lines(x=x, y=maxes * over.rescale, lty="dotted", type="h", col=over.col.max.line, ...)
		lines(x=x, y=means * over.rescale, type="h", col=over.col.mean.line, ...)
		points(x=x, y=maxes * over.rescale, col=over.col.max.pt, pch=24, bg=over.col.max.fill, ...)
		points(x=x, y=means * over.rescale, col=over.col.mean.pt, pch=1, ...)
		points(x=x[which(maxes==0)], y=rep(0, sum(maxes==0)), col=empty.col, pch=16)
		# abline(h=label.thresh, lty="dotted", col=over.col, ...)
		
		label.idx <- which(maxes > label.thresh)
		for ( ii in label.idx )
		{
			text(x=x[ii], y=maxes[ii] * over.rescale, labels=col_levels[ii], col=label.col, pos=label.pos ) 
		}
	}
	
	if ( intermediates )
	{
		invisible(list(map=result, data=dat, rows=row_levels,
					   cols=col_levels, field=field, x=x, mean=means, max=maxes))
	}
	else
	{
		invisible( result )
	}
}

best_fit <- function ( best_fit=NULL, intermediates=TRUE, plot=TRUE, dist.fields=c("dist_L1", "dist_Cosine"), main="Closest Model Traces", legend.pos="topright", clut=1:7, convert.func=function(x){ paste("Minimum", substring(x, 6)) }, use_ylim=TRUE, ... )
{
	# we're willing to duplicate some effort here, but let's
	# not reload huge tables when we don't have to...
	if ( class(best_fit) == "best_fit" )
	{
		results <- best_fit$results
		distances <- best_fit$distances
	}
	else
	{
		results <- read.table("results.txt", header=TRUE)
		distances <- read.table("distances.txt", header=TRUE)
	}
	
	# top few rows of results contain meta info, with NA job and rep
	# 1 - time points
	# 2:(N_inputs + 1) - input time series
	# N_inputs + 2 - measured value
	
	# remaining are all results rows and there should be same number
	# as there are rows in distances
	
	first.col <- which(colnames(results) == 't0')
	last.col <- dim(results)[2]
	tt <- first.col:last.col
	
	first.row <- which(!is.na(results$job))[1]
	last.row <- dim(results)[1]
	
	times <- as.numeric(results[1, tt])
	measured <- as.numeric(results[first.row - 1, tt])
	traces <- as.matrix(results[first.row:last.row, tt])
	
	measured.name <- results$species[first.row]
	
	if ( plot )
	{
		if ( class(best_fit) == "best_fit" && use_ylim )
		{
			plot(measured ~ times, type="l", col=clut[1],
				 xlab="Time", ylab=measured.name, main=main, ylim=best_fit$ylim, ...)
		}
		else
		{
			plot(measured ~ times, type="l", col=clut[1], xlab="Time", ylab=measured.name, main=main, ...)
		}
	}
	
	best <- NULL
	for ( ii in 1:length(dist.fields) )
	{
		dists <- distances[[dist.fields[ii]]]
		best.idx = which(dists==min(dists))
		nbest <- length(best.idx)
		
		if ( plot )
		{
			lines(x=times, y=traces[best.idx[1],], col=clut[ii + 1])
		}
		
		best <- rbind( best, cbind( data.frame(dist.field=rep(dist.fields[ii], nbest)), distances[best.idx,] ) )
	}
	
	if ( plot )
	{
		legend(legend.pos, legend=c( "Measured Signal", sapply(dist.fields, convert.func)), lty="solid", col=clut)
	}
	
	if ( intermediates )
	{
		ally <- c(measured, as.vector(traces[best$job + 1,]))
		retval <- list(results=results,
				 	   distances=distances,
					   traces=traces,
					   measured=measured,
					   measured.name=measured.name,
					   times=times,
					   best=best,
					   ylim=range(ally))
		class(retval) <- "best_fit"
		invisible(retval)
	}
	else
	{
		invisible(best)
	}
}
