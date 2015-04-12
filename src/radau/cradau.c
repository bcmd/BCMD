/* C-Interface implementation to the RADAU/RADAU5-Code written by E.Hairer and G. Wanner.
   by Michael Hauth, 2001.
   mailto: Michael.Hauth@wsi-gris.uni-tuebingen.de */


#include "./radau.h"
#include <stdlib.h>
#include <malloc.h>

void cradau(int n,
		   void fcn(int*,double*,double*,double*,double*,int*),
		   double x, double *y, double xend, double h,
           double rtol, double atol, 
		   void jac(int*, double*, double*, double*, int*, double*, double*),
		    int ijac, int mljac, int mujac,
		   void mas(int *n,double *am, int *lmas, double *rpar, int *ipar),
		    int imas, int mlmas, int mumas,
		   void solout(int*,double*,double*,double*,double*,int*,int*,double*,int*,int*),
		    int iout,
		   double *work, int *iwork,
		   double *rpar, int *ipar, int *idid)
{
	int N=n;
	double X=x;
	double XEND=xend;
	double H=h;
	/* we have scalar tolerances */
	int ITOL=0;
	double RTOL=rtol;
	double ATOL=atol;

	int IJAC=ijac;
	int MLJAC=mljac;
	int MUJAC=mujac;

	int IMAS=imas;
	int MLMAS=mlmas;
	int MUMAS=mumas;

	int IOUT=iout;
	
	double *WORK;
	int LWORK;
	int *IWORK;
	int LIWORK=1;
         
    int nsmax=iwork[11];
	int ljac, lmas, le;
	
	/* computing the size of the working arrays */

	if (mljac==n){  /* full jacobian */
		ljac=n;
		le=n;
	}
	else {          /* banded case */
		ljac=mljac+mujac+1;
		le=2*mljac+mujac+1;
	}
	
    if (imas==0)    /* no mass */
		lmas=0;
	else
		if (mlmas=n)/* full mass */
			lmas=n;
		else        /*banded mass */
			lmas=mlmas+mumas+1;

	if (nsmax==0)
		nsmax=7;

	/* allocation of workspace */

	LWORK = n*(ljac+lmas+nsmax*le+3*nsmax+3)+20;
	LIWORK = (2+(nsmax-1)/2)*n+20;

	WORK= malloc((LWORK) * sizeof(double) );
	IWORK= malloc(LIWORK * sizeof(int) );

	/* copy parameters */
	for (le=0;le<20;++le){
		WORK[le] = work[le];
		IWORK[le] = iwork[le];
	}
	

   RADAU(&N, fcn, &X, y, &XEND, &H,
   &RTOL, &ATOL, &ITOL,
   jac, &IJAC, &MLJAC, &MUJAC,
   mas, &IMAS, &MLMAS, &MUMAS,
   solout, &IOUT,
   WORK, &LWORK, IWORK, &LIWORK,
   rpar, ipar, idid);
   
   /* copy results */
   for (le=0;le<20;++le){
	   work[le] = WORK[le];
	   iwork[le] = IWORK[le];
   }
   
   free(WORK);
   free(IWORK);
   
}

void cradau5(int n,
		   void fcn(int*,double*,double*,double*,double*,int*),
		   double x, double *y, double xend, double h,
           double rtol, double atol, 
		   void jac(int*, double*, double*, double*, int*, double*, double*),
		    int ijac, int mljac, int mujac,
		   void mas(int *n,double *am, int *lmas, double *rpar, int *ipar),
		    int imas, int mlmas, int mumas,
		   void solout(int*,double*,double*,double*,double*,int*,int*,double*,int*,int*),
		    int iout,
		   double *work, int *iwork,
		   double *rpar, int *ipar, int *idid)
{
	int N=n;
	double X=x;
	double XEND=xend;
	double H=h;
	/* we have scalar tolerances */
	int ITOL=0;
	double RTOL=rtol;
	double ATOL=atol;

	int IJAC=ijac;
	int MLJAC=mljac;
	int MUJAC=mujac;

	int IMAS=imas;
	int MLMAS=mlmas;
	int MUMAS=mumas;

	int IOUT=iout;
	
	double *WORK;
	int LWORK;
	int *IWORK;
	int LIWORK=1;
         
	int ljac, lmas, le;
	
	/* computing the size of the working arrays */

	if (mljac==n){  /* full jacobian */
		ljac=n;
		le=n;
	}
	else {          /* banded case */
		ljac=mljac+mujac+1;
		le=2*mljac+mujac+1;
	}
	
    if (imas==0)    /* no mass */
		lmas=0;
	else
		if (mlmas=n)/* full mass */
			lmas=n;
		else        /*banded mass */
			lmas=mlmas+mumas+1;


	/* allocation of workspace */
	LWORK = n*(ljac+lmas+3*le+12)+20;
	LIWORK = 3*n+20;

	WORK= malloc(LWORK * sizeof(double) );
	IWORK= malloc(LIWORK * sizeof(int) );

	/* copy parameters */
	for (le=0;le<20;++le){
		WORK[le] = work[le];
		IWORK[le] = iwork[le];
	}
	

   RADAU5(&N, fcn, &X, y, &XEND, &H,
   &RTOL, &ATOL, &ITOL,
   jac, &IJAC, &MLJAC, &MUJAC,
   mas, &IMAS, &MLMAS, &MUMAS,
   solout, &IOUT,
   WORK, &LWORK, IWORK, &LIWORK,
   rpar, ipar, idid);
   
   /* copy results */
   for (le=0;le<20;++le){
	   work[le] = WORK[le];
	   iwork[le] = IWORK[le];
   }
   
   free(WORK);
   free(IWORK);
   
}

double ccontra(int i, double s, double *cont, int *lrc)
{
	int I=i;
	double S=s;

	return CONTRA(&I, &S, cont, lrc);
}

double ccontr5(int i, double s, double *cont, int *lrc)
{
	int I=i;
	double S=s;

	return CONTR5(&I, &S, cont, lrc);
}
