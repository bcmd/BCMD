#! /usr/bin/env python

import sys
import numpy as np

def per_ext(x,a):
	l=len(x)
	if l%2 != 0:
		t=x[l-1]
		x=np.append(x,t)
		l=len(x)
	
	for i in range(a):
		post=x[2*i]
		pre=x[l-1]
		x=np.append(x,post)
		x=np.append(pre,x)
	
	return x

def symm_ext(x,a):
	
	for i in range(a):
		l=len(x)
		pre=x[1+i*2]
		post=x[l-(i+1)*2]
		x=np.append(x,post)
		x=np.append(pre,x)
	
	return x


def circshift(x,a):
	if np.abs(a) > len(x):
		a=np.sign(a) * (np.abs(a)%len(x))
		
	if a < 0:
		a= (len(x)+a) % len(x)
	
	for i in range(a):
		temp=x[0]
		x=np.append(x,temp)
		x=np.delete(x,[0])
	
	return x
	
def circshift2d(x,a,b):
	rows=np.size(x,0)
	cols=np.size(x,1)
	
	for i in range(rows):
		x[i,:]=circshift(x[i,:],a)
		
	for j in range(cols):
		x[:,j]=circshift(x[:,j],b)		
		
	return x			


def per_ext2d(x,a):
	rows=np.size(x,0)
	cols=np.size(x,1)
	if cols%2 != 0:
		cols2=int(cols+1)
	else:
		cols2=cols
		
	if rows%2 != 0:
		rows2=int(rows+1)
	else:
		rows2=rows	
		
	
	temp_vec=np.ndarray(shape=(rows,cols2+2*a))
	y=np.ndarray(shape=(rows2+2*a,cols2+2*a))

	for i in range(rows):
		temp_vec[i,:]=per_ext(x[i,:],a)
	
	colx=np.size(temp_vec,1)
		

	for j in range(colx):
		temp=temp_vec[:,j]
		y[:,j]=per_ext(temp,a)

	return y

def symm_ext2d(x,a):
	rows=np.size(x,0)
	cols=np.size(x,1)

	y=np.zeros((rows+2*a,cols+2*a))
	for i in range(rows):
		
		y[i+a,:]=symm_ext(x[i,:],a)

	for j in range(cols+2*a):
		y[:,j]=symm_ext(y[a:rows+a,j],a)

	return y

