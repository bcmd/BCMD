      SUBROUTINE RADAUTEST(n,fcn,x,y,xend,h,
     &                     rtol,atol,itol,jac,
     &                     ijac,mljac,mujac,mas,
     &                     imas,mlmas,mumas,
     &                     solout,iout,work,lwork,
     &                     iwork,liwork,rpar,ipar,idid)
      implicit double precision (a-h,o-z)
      dimension y(n),atol(*),rtol(*),work(lwork),iwork(liwork)
      dimension rpar(*),ipar(*)
      integer i
      write(6,*) 'Dimension        ', n
      write(6,*) 'Initial Time     ', x
      write(6,*) 'End Time         ', xend
      write(6,*) 'Initial Stepsize ', h
      if (itol.eq.0) then
        write(6,*) 'RTol/ATol        ', rtol(1),'/',atol(1)
      else
        write(6,*) 'Vector Tolerances'
      endif
      write(6,*) 'Initial Value    ', y
      if (ijac.eq.0) then
        write(6,*) 'Internal Jacobian'
      else
        write(6,*) 'Jacobian provided'
      endif
      if (imas.eq.0) then
        write(6,*) 'Explicit equation'
      else
        write(6,*) 'Mass matrix provided'
      endif
      if (iout.eq.0) then
        write(6,*) 'Not using solout'
      else
        write(6,*) 'Calling solout function'
      endif
      write(6,*) 'Sophisticated parameters:'
      do i=1,20
        write(6,100) i,work(1)
      enddo
100   format('   work(',1i2,') = ',1f4.2)
      do i=1,20
        write(6,101) i,iwork(1)
      enddo
101   format('  iwork(',1i2,') = ',1i4)
      end

      subroutine print_mat(n, m, A)
      integer n,m,i,j
      double precision A
      dimension A(n,m)
      do i=1,n
        do j=1,m
          write(6,*) i,j,A(i,j)
        enddo
      enddo
      end
