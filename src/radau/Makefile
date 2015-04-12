#####################################################################
#
#  Makefile for radau libraries
#  radau: radau with decsol (no further libs necessary)
#  lapack: radau ready to use with a (user supplied) lapack
#
#####################################################################
CC = gcc
CXX = g++
#F77 = @F77@
FC = gfortran
CFLAGS = -g -O2
CXXFLAGS= -g -O2
FFLAGS = -g -O2

AR      =       ar crs

HEADERS =	radau.h

SOURCES1 =	radau.f\
		radau5.f\
		radauTest.f

SOURCES2 =	dc_decsol.f\
		decsol.f

SOURCES3 = 	dc_lapack.f\
		lapack.f\
		lapackc.f

OBJECTS1 =	objfiles/radau.o\
		objfiles/radau5.o\
		objfiles/radauTest.o

OBJECTS2 =	objfiles/dc_decsol.o\
		objfiles/decsol.o

OBJECTS3 = 	objfiles/dc_lapack.o\
		objfiles/lapack.o\
		objfiles/lapackc.o



.SUFFIXES: .c .f .f90

radau: ../../common/lib/libradauLapack.a ../../common/lib/libradaudecsol.a ;

#.c.o: $(HEADERS)
#	$(CC) -c $(CFLAGS) $(INCPATH) -o $@ $<
objfiles/%.o: %.f
	$(FC) -c $(FFLAGS) $(INCPATH) -o $@ $<
#.f.o: $(HEADERS)
#	$(FC) -c $(FFLAGS) $(INCPATH) -o $@ $<
#.f90.o:
#	$(F90) -c $(FFLAGS) $(INCPATH) -o $@ $<

../../common/lib/libradauLapack.a: $(OBJECTS1)  $(OBJECTS3)
	$(AR) ../../common/lib/libradauLapack.a $(OBJECTS1)  $(OBJECTS3)

../../common/lib/libradaudecsol.a: $(OBJECTS1) $(OBJECTS2)
	$(AR) ../../common/lib/libradaudecsol.a $(OBJECTS1)  $(OBJECTS2)

clean:
	rm -f $(OBJECTS1) $(OBJECTS2)  $(OBJECTS3) *~

