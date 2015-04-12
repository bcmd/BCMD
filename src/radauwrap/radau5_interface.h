/* Wrapper interface for the RADAU5 Fortran code. Provides
   some memory management and hides a bunch of tedious boilerplate. */

#ifndef RADAU5_INTERFACE_H
#define RADAU5_INTERFACE_H

/* Function to calculate the value of the system at a given time point */
typedef void (*RadauRHS)(int* N, double* X, double* Y, double* F, double* RPAR, int* IPAR);

/* Function to output solution. Details TBD. */
typedef void (*RadauOut)(int* NR, double* XOLD, double* X, double* Y, double* CONT,
                         int* LRC, int* N, double* RPAR, int* IPAR, int* IRTRN);

/* Allocate the memory, releasing any previously allocated version.
   Note that this is potentially dangerous if the caller has stashed
   a previously obtained pointer, but we're just going to trust them
   not to do anything that silly.
   (Stand by for inevitable kicking of self in 6 months' time...)
   
   If there are no algebraics and requireMass is false, no mass matrix
   is be generated.
   
   Returns 0 if successful, -1 if there was an allocation failure. */
extern int radau5_alloc ( unsigned int nDiffEqs,
                          unsigned int nAlgebraics,
                          int diagonal,
                          int requireMass,
                          unsigned int nDoubleParams,
                          unsigned int nIntParams );

/* Deallocates any memory previously allocated by radau5_dealloc. */
extern void radau5_dealloc ();

/* Invoke the solver with the current configuration and
   supplied client functions. starty can be NULL, otherwise
   it should be an array of initial values for all problem
   variables. rhs and/or out can also be NULL, in which case
   internal debug functions will be used. You probably don't
   want to do that in real models.
   
   Returns an integer result code from the solver:
     1: success
     2: successful but interrupted by output function
    -1: inconsistent input
    -2: larger NMAX needed
    -3: step size becomes too small
    -4: matrix is repeatedly singular
 */
extern int radau5_solve ( double startx, double endx, double* starty,
                          RadauRHS rhs, RadauOut out );

/* Setters for some parameters that are buried at arbitrary array
   locations in the Fortran interface. (All of these are given
   probably-reasonable default values on allocation.) */
extern void radau5_set_rounding ( double rounding );
extern void radau5_set_jacrecompute ( double jacrecompute );
extern void radau5_set_maxstepsize ( double maxstepsize );
extern void radau5_set_maxsteps ( unsigned int maxsteps );
extern void radau5_set_maxnewton ( unsigned int maxnewton );
extern void radau5_set_tolerances ( double diffrelative, double diffabsolute,
                                    double algrelative, double algabsolute );

/* Get pointers to the arrays allocated for variables and
   parameters. Note that holding onto these after
   de- or re-allocation will lead to tears. */
extern double* radau5_getDoubleParams ();
extern int* radau5_getIntParams ();
extern double* radau5_getY ();
extern double* radau5_getRelativeTolerances ();
extern double* radau5_getAbsoluteTolerances ();

/* As above, but also note that this may legitimately be NULL. */
extern double* radau5_getMassMatrix();

#endif


