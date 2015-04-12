/* Boilerplate C file providing an interface to the RADAU5 solver.
   Provides functions for allocating and initialising the memory
   used in arguments to the Fortran code, and for releasing it
   again. This interface provides many fewer options than the
   RADAU5 function itself, but should also be a lot easier to
   use. The relatively few things that need to be configured
   can be done via function calls, and all this code should
   be able to be linked unmodified into the model executable.
   At least, I hope so... */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "radau.h"
#include "radau5_interface.h"

/* uncomment this (or define elsewhere) for an obscene amount of interface logging
   (note that this is separate from the logging below) */
/* #define RADAU_SUPER_DEBUG */

#ifdef RADAU_SUPER_DEBUG
#include <time.h>
#endif

/* uncomment this (or define elsewhere) for some investigative logging */
/* #define RADAU_DEBUG */

/* uncomment this (or define elsewhere) to include a main function */
/* #define RADAU_DEBUG_MAIN */

/* Main requires debug... */
#ifdef RADAU_DEBUG_MAIN
#ifndef RADAU_DEBUG
#define RADAU_DEBUG
#endif
#endif

/* We keep all the data in a bunch of static (ie, compilation unit
   global) variables, accessible via the interface functions. */

/* Variables defining the system */
static unsigned int N_DIFF_EQS = 0;
static unsigned int N_ALGEBRAICS = 0;
static unsigned int N_VARS = 0;
static int DIAGONAL = 0;
static int EXPLICIT_MASS = 0;
static unsigned int N_DOUBLE_PARAMS = 0;
static unsigned int N_INT_PARAMS = 0;

/* Ordinary (single-valued) storage variables passed to RADAU5.
   Variable names correspond to the RADAU5 parameters. Many of
   these are never changed from their defaults. Those that need
   to be set explicitly are commented accordingly. */
static double x = 0;            /* set at invocation time */
static double h = 1e-6;
static double xend = 0;         /* set at invocation time */
static int itol = 1;            /* always use vector tolerances */
static int ijac = 0;
static int mljac = 0;           /* set to N_VARS at alloc time */
static int mujac = 0;
static int imas = 0;            /* set to (EXPLICIT_MASS ? 1 : 0) at alloc time */
static int mlmas = 0;           /* set to (DIAGONAL ? 0 : N_VARS) at alloc time */
static int mumas = 0;
static int iout = 1;

static int lwork = 0;           /* set at alloc time */
static int liwork = 0;          /* set at alloc time */

static int idid = 0;

static int DUMMY = 0;           /* general purpose location for pointers we will never use */

/* Vector variables (ie, requiring memory management). */
static double* y = 0;
static double* mass = 0;
static int* iwork = 0;
static double* work = 0;
static double* rpar = 0;
static int* ipar = 0;
static double* rtol = 0;
static double* atoler = 0;    /* note: name changed to avoid clash with stdlib function */

/* Paraphernalia used for interface logging */
#ifdef RADAU_SUPER_DEBUG
static FILE* DB_iwork_file = 0;
static FILE* DB_work_file = 0;
static FILE* DB_rpar_file = 0;
static FILE* DB_invoke_file = 0;
#endif

/* Prototypes for internal functions */
void dummy_jac (int*, double*, double*, double*, int*, double*, double*);
void diag_mass (int* n, double* am, int* lmas, double* rpar, int* ipar);
void full_mass (int* n, double* am, int* lmas, double* rpar, int* ipar);
void dummy_RHS (int* n, double* x, double* y, double* f, double* rpar, int* ipar);
void dummy_out(int* nr, double* xold, double* x, double* y, double* cont,
               int* lrc, int* n, double* rpar, int* ipar, int* irtrn);

#ifdef RADAU_DEBUG
void dump_all ();
#endif

#ifdef RADAU_SUPER_DEBUG
void super_dump_all ( double startx, double endx );
#endif

/* Dummy Jacobian function.

   Note that the type of the ipar parameter is incorrect -- this is to
   match the (wrong) type declared by radau.h -- if this were actually used
   we would have to cast appropriately, but as it is we don't care.  */
void dummy_jac (int* n, double* x, double* y, double* dfy, int* ldfy, double* rpar, double* ipar)
{
    /* do nothing */
}

/* Mass function variants for diagonal and non-diagonal variations. (We also
   pass one of these as a dummy in the purely differential case.) */
void diag_mass (int* n, double* am, int* lmas, double* rpar, int* ipar)
{
#ifdef RADAU_DEBUG
    int ii;
    char c;
    
    /* AM should be a single vector of length N_VARS */
    printf("diag_mass: n = %d, lmas = %d, N_VARS = %d\n", *n, *lmas, N_VARS);
    printf("---\n");
    for ( ii = 0; ii < N_VARS; ++ii )
    {
        c = (ii == N_VARS - 1) ? '\n' : '\t';
        printf("%g%c", mass[ii], c);
    }
    printf("---\n");
#endif
    memcpy ( am, mass, N_VARS * sizeof(double) );    
}

void full_mass (int* n, double* am, int* lmas, double* rpar, int* ipar)
{
#ifdef RADAU_DEBUG
    int ii, jj;
    char c;
    
    /* AM should be a matrix of size N_VARS x N_VARS */
    printf("full_mass: n = %d, lmas = %d, N_VARS = %d\n", *n, *lmas, N_VARS);
    printf("---\n");
    for ( ii = 0; ii < N_VARS; ++ii )
    {
        for ( jj = 0; jj < N_VARS; ++jj )
        {
            /* Note: we are printing this in column-major order, which
               should transpose it from Fortran format into natural
               viewing format in the output */
            c = (jj == N_VARS - 1) ? '\n' : '\t';
            printf("%g%c", mass[jj * N_VARS + ii], c);
        }
    }
#endif
    memcpy ( am, mass, N_VARS * N_VARS * sizeof(double) );
}

/* Dummy RHS function for testing purposes */
void dummy_RHS (int* n, double* x, double* y, double* f, double* rpar, int* ipar)
{
    int ii;
    
#ifdef RADAU_DEBUG
    printf("dummy_RHS: n = %d\n", *n);
    printf("dummy_RHS: x = %g\n", *x);
    printf("dummy_RHS: y = ");
    for ( ii = 0; ii < *n; ++ii )
    {
        if ( ii == *n - 1 )
            printf("%g\n", y[ii]);
        else
            printf("%g, ", y[ii]); 
    }
#endif

    /* Not sure what makes for a sensible dummy function here. For the moment,
       just copy across -- ie, func is just y' = y */
    for ( ii = 0; ii < *n; ++ii )
        f[ii] = y[ii];
}

/* Dummy output function that just dumps some info. */
void dummy_out(int* nr, double* xold, double* x, double* y, double* cont,
               int* lrc, int* n, double* rpar, int* ipar, int* irtrn)
{
#ifdef RADAU_DEBUG
    int ii;
    printf("dummy_out: nr = %d, n = %d\n", *nr, *n);
    printf("dummy_out: xold = %g, x = %g\n", *xold, *x );
    printf("dummy_out: y = ");
    for ( ii = 0; ii < *n; ++ii )
    {
        if ( ii == *n - 1 )
            printf("%g\n", y[ii]);
        else
            printf("%g, ", y[ii]); 
    }
#endif
    /* never interrupt -- this is probably unnecessary, but anyway */
    *irtrn = 0;
}

/* Allocate the memory, releasing any previously allocated version.
   Note that this is potentially dangerous if the caller has stashed
   a previously obtained pointer, but we're just going to trust them
   not to do anything that silly.
   (Stand by for inevitable kicking of self in 6 months' time...)
   
   If there are no algebraics and requireMass is false, no mass matrix
   will be generated, and RADAU5 will use an internal identity matrix.
   
   Returns 0 if successful, -1 if there was an allocation failure. */
int radau5_alloc ( unsigned int nDiffEqs,
                   unsigned int nAlgebraics,
                   int diagonal,
                   int requireMass,
                   unsigned int nDoubleParams,
                   unsigned int nIntParams )
{
    int ii;
#ifdef RADAU_SUPER_DEBUG
    time_t timestamp;
    char* timestr;
    const size_t BUF_SIZE = 1024;
    char buffer[BUF_SIZE];
#endif
    
    if ( y )
    {
        radau5_dealloc();
    }
    
    N_DIFF_EQS = nDiffEqs;
    N_ALGEBRAICS = nAlgebraics;
    N_DOUBLE_PARAMS = nDoubleParams;
    N_INT_PARAMS = nIntParams;
    N_VARS = N_DIFF_EQS + N_ALGEBRAICS;
    DIAGONAL = diagonal;
    EXPLICIT_MASS = requireMass || nAlgebraics > 0;
    
    y = (double*)calloc(N_VARS, sizeof(double));
    
    if ( EXPLICIT_MASS )
    {
        if (DIAGONAL)
            mass = (double*)calloc(N_VARS, sizeof(double));
        else
            mass = (double*)calloc(N_VARS * N_VARS, sizeof(double));
    }
    else
        mass = (double*) &DUMMY;
    
    /* for simplicity we always allocate some space for the mass matrix
       even when using the identity */
    lwork = 5 * N_VARS * N_VARS + 12 * N_VARS + 20;
    work = (double*)calloc(lwork, sizeof(double));
    liwork = 3 * N_VARS + 20;
    iwork = (int*)calloc(liwork, sizeof(int));
    
    rtol = (double*)calloc(N_VARS, sizeof(double));
    atoler = (double*)calloc(N_VARS, sizeof(double));
    
    if ( nDoubleParams )
        rpar = (double*)calloc( nDoubleParams, sizeof(double));
    
    if ( nIntParams )
        ipar = (int*)calloc(nIntParams, sizeof(int));

    if ( y == 0 || mass == 0
         || work == 0 || iwork == 0
         || rtol == 0 || atoler == 0
         || ( rpar == 0 && nDoubleParams != 0 )
         || ( ipar == 0 && nIntParams != 0 ) )
    {
        radau5_dealloc();
        return(-1);
    }
    
    mljac = N_VARS;
    
    if ( EXPLICIT_MASS )
    {
        imas = 1;

        if ( DIAGONAL )
        {
            for ( ii = 0; ii < N_DIFF_EQS; ++ii )
                mass[ii] = 1;
            mlmas = 0;
        }
        else
        {
            for ( ii = 0; ii < N_DIFF_EQS; ++ii )
                mass[ii * N_VARS + ii] = 1;
            mlmas = N_VARS;
        }
    }
    else
    {
        imas = 0;
        mlmas = N_VARS;
    }
        
    iwork[4] = (int) N_DIFF_EQS;
    iwork[5] = (int) N_ALGEBRAICS;
    
    /* Initial values taken from Murad's code
       -- might reassess these at some point */
    radau5_set_rounding ( 1e-15 );
    radau5_set_jacrecompute ( 0.001 );
    radau5_set_maxstepsize ( 100 );
    radau5_set_maxsteps ( 100000 );
    radau5_set_maxnewton ( 2 );
    radau5_set_tolerances ( 1e-6, 1e-10, 2e-3, 2e-5 );


#ifdef RADAU_SUPER_DEBUG
    /* this is ugly and risky, but hopefully we won't be using it much */
    time(&timestamp);
    timestr = ctime(&timestamp);
    
    if ( snprintf(buffer, BUF_SIZE, "DB_iwork_%s.txt", timestr) > 0 )
        DB_iwork_file = fopen(buffer, "w");
    if ( snprintf(buffer, BUF_SIZE, "DB_work_%s.txt", timestr) > 0 )
        DB_work_file = fopen(buffer, "w");
    if ( snprintf(buffer, BUF_SIZE, "DB_rpar_%s.txt", timestr) > 0 )
        DB_rpar_file = fopen(buffer, "w");
    if ( snprintf(buffer, BUF_SIZE, "DB_invoke_%s.txt", timestr) > 0 )
        DB_invoke_file = fopen(buffer, "w");
#endif
    
    return 0;
}

/* Deallocate everything */
void radau5_dealloc ()
{
    free(y); y = 0;
    
    if ( mass != (double*) &DUMMY )
    {
        free(mass);
        mass = 0;
    }
    
    free(iwork); iwork = 0; liwork = 0;
    free(work); work = 0; lwork = 0;
    free(rpar); rpar = 0;
    free(ipar); ipar = 0;
    free(rtol); rtol = 0;
    free(atoler); atoler = 0;
    
    N_DIFF_EQS = 0;
    N_ALGEBRAICS = 0;
    N_DOUBLE_PARAMS = 0;
    N_INT_PARAMS = 0;
    N_VARS = 0;
    DIAGONAL = 0;

#ifdef RADAU_SUPER_DEBUG
    if ( DB_iwork_file )
        fclose(DB_iwork_file);
    
    if ( DB_work_file )
        fclose(DB_work_file);
    
    if ( DB_rpar_file )
        fclose(DB_rpar_file);
    
    if ( DB_invoke_file )
        fclose(DB_invoke_file);
    
    DB_iwork_file = 0;
    DB_work_file = 0;
    DB_rpar_file = 0;
    DB_invoke_file = 0;
#endif
}

/* Accessors */

void radau5_set_rounding ( double rounding )
{
    if ( work )
        work[0] = (rounding > 0) ? rounding : 0;
}

void radau5_set_jacrecompute ( double jacrecompute )
{
    if ( work )
        work[2] = jacrecompute;
}

void radau5_set_maxstepsize ( double maxstepsize )
{
    if ( work )
        work[6] = (maxstepsize > 0) ? maxstepsize : 0.1;
}

void radau5_set_maxsteps ( unsigned int maxsteps )
{
    if ( iwork )
        iwork[1] = (int) maxsteps;
}

void radau5_set_maxnewton ( unsigned int maxnewton )
{
    if ( iwork )
        iwork[3] = maxnewton;
}

void radau5_set_tolerances ( double diffrelative, double diffabsolute,
                             double algrelative, double algabsolute )
{
    int ii = 0;

    for ( ; ii < N_DIFF_EQS; ++ii )
    {
        rtol[ii] = diffrelative;
        atoler[ii] = diffabsolute;
    }
    
    for ( ; ii < N_VARS; ++ii )
    {
        rtol[ii] = algrelative;
        atoler[ii] = algabsolute;
    }    
}

double* radau5_getDoubleParams ()
{
    return rpar;
}

int* radau5_getIntParams ()
{
    return ipar;
}

double* radau5_getY ()
{
    return y;
}

double* radau5_getRelativeTolerances ()
{
    return rtol;
}

double* radau5_getAbsoluteTolerances ()
{
    return atoler;
}

double* radau5_getMassMatrix ()
{
    return mass;
}

/* Invocation */
int radau5_solve ( double startx, double endx, double* starty,
                   RadauRHS rhs, RadauOut out )
{
    int ii;
    
    int N = (int) N_VARS;
    
    /* initialise */
    x = startx;
    xend = endx;
    
    /* client can pass a NULL y if initialising elsewhere (or
       indeed if happy with all ys starting at 0 */
    if ( starty )
    {
        for ( ii = 0; ii < N_VARS; ++ii )
            y[ii] = starty[ii];
    }
    
    /* we may need to clear out some leftovers from a previous run
       (the bounds on these loops have been identified empirically) */
    for ( ii = 7; ii < 20; ++ii )
        work[ii] = 0;
    
    for ( ii = 6; ii < 20; ++ii )
        iwork[ii] = 0;
    
    if ( ! rhs )
        rhs = dummy_RHS;
    
    if ( ! out )
        out = dummy_out;
    
#ifdef RADAU_DEBUG
    printf("\n*** RADUA5_SOLVE ***\n");
    dump_all();
    printf("\n");
#endif

#ifdef RADAU_SUPER_DEBUG
    super_dump_all( startx, endx );
#endif
    
    RADAU5 ( &N, rhs, &x, y, &xend, &h, rtol, atoler, &itol,
             dummy_jac, &ijac, &mljac, &mujac,
             DIAGONAL ? diag_mass : full_mass, &imas, &mlmas, &mumas,
             out, &iout, work, &lwork, iwork, &liwork,
             rpar, ipar, &idid );
    
    return idid;
}

#ifdef RADAU_DEBUG
void dump_all ()
{
    printf("N_DIFFEQS = %d\n", N_DIFF_EQS);
    printf("N_ALGEBRAICS = %d\n", N_ALGEBRAICS);
    printf("N_VARS = %d\n", N_VARS);
    printf("DIAGONAL = %d\n", DIAGONAL);
    printf("N_DOUBLE_PARAMS = %d\n", N_DOUBLE_PARAMS);
    printf("N_INT_PARAMS = %d\n", N_INT_PARAMS);
    
    printf("x = %g\n", x);
    printf("h = %g\n", h);
    printf("xend = %g\n", xend);
    printf("rtol[0] = %g\n", rtol[0]);
    printf("atoler[0] = %g\n", atoler[0]);
    printf("itol = %d\n", itol);
    printf("ijac = %d\n", ijac);
    printf("mljac = %d\n", mljac);
    printf("mujac = %d\n", mujac);
    printf("imas = %d\n", imas);
    printf("mlmas = %d\n", mlmas);
    printf("mumas = %d\n", mumas);
    printf("iout = %d\n", iout);
    printf("lwork = %d\n", lwork);
    printf("liwork = %d\n", liwork);
    printf("idid = %d\n", idid);
    
    /* skip the vectors for now */
    
    /* stats from BRAINCIRC use */
    printf("fcn= %i jac= %i step= %i accpt= %i rejct= %i dec= %i sol= %i\n", iwork[13],iwork[14],iwork[15],iwork[16],iwork[17],iwork[18],iwork[19]);

}
#endif

#ifdef RADAU_SUPER_DEBUG
void super_dump_all  ( double startx, double endx )
{
    int ii;
    
    if ( DB_iwork_file && liwork > 0 )
    {
        for ( ii = 0; ii < (liwork - 1); ++ii )
            fprintf(DB_iwork_file, "%d\t", iwork[ii]);
        fprintf(DB_iwork_file, "%d\n", iwork[ii]);
    }
    
    if ( DB_work_file && lwork > 0 )
    {
        for ( ii = 0; ii < (lwork - 1); ++ii )
            fprintf(DB_work_file, "%g\t", work[ii]);
        fprintf(DB_work_file, "%g\n", work[ii]);
    }
    
    if ( DB_rpar_file && N_DOUBLE_PARAMS > 0  )
    {
        for ( ii = 0; ii < (N_DOUBLE_PARAMS - 1); ++ii )
            fprintf(DB_rpar_file, "%g\t", rpar[ii]);
        fprintf(DB_rpar_file, "%g\n", rpar[ii]);
    }
    
    if ( DB_invoke_file )
    {
        fprintf(DB_invoke_file, "%g\t%g", startx, endx);
        for ( ii = 0; ii < N_VARS; ++ii )
            fprintf(DB_invoke_file, "\t%g", y[ii]);
        fprintf(DB_invoke_file, "\n");
    }
}
#endif

#ifdef RADAU_DEBUG_MAIN
int main ( int argc, char** argv )
{
    double startY[6] = { 1.2, 3.1, 2.1, 10.6, 8.8, 5.6 };
    double startX = 0;
    double endX = 10;
    
    unsigned int nDEs = 4;
    unsigned int nAlg = 2;
    int diag = 1;
    int reqMass = 0;
    int nDbl = 10;
    int nInt = 10;
    int err = 0;
    
    printf( "Initialising interface with nDiffEq=4, nAlgebraic=2\n" );
    
    err = radau5_alloc ( nDEs, nAlg, diag, reqMass, nDbl, nInt );
    if ( err )
    {
        printf( "Initialisation failed with code: %d\n", err );
        return err;
    }
    
    dump_all();
    
    printf( "Invoking RADAU5\n" );
    
    err = radau5_solve ( startX, endX, startY, NULL, NULL );
    
    printf( "RADAU5 finished with return code: %d\n", err );
    
    printf( "Deallocating interface\n" );
    
    radau5_dealloc();
    
    return 0;
}
#endif

