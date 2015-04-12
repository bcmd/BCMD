#! /usr/bin/env python

import sys
import numpy as np
import dwt
from math import sqrt

def denoise(sig,mode_denoise,nm_dn,J_dn,dn_method,dn_thresh):
	signal=np.array(sig)
	sig_size=int(len(signal))
	max_dec=int(np.floor(np.log2(sig_size)))-1
	if J_dn >= max_dec:
		J_dn=max_dec
	
	if dn_method == "visushrink" or dn_method == "visu":
		if mode_denoise == "swt":
			[dwt_output,length]=dwt.swt(signal,J_dn,nm_dn)
			dwt_len=int(len(dwt_output))
			dwt_med=np.abs(dwt_output)
			sigma=np.median(dwt_med)
			td=sqrt(2.0 * np.log(dwt_len)) * sigma / 0.6745
			
			if dn_thresh == "hard":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) <= td:
						dwt_output[iter]=0
						
			elif dn_thresh == "soft":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) >= td:
						dwt_output[iter]=np.sign(dwt_output[iter])*(np.abs(dwt_output[iter]) - td)
					else:
						dwt_output[iter]=0
			
			output=dwt.iswt(dwt_output,J_dn,nm_dn)	
		
		elif mode_denoise == "per" or mode_denoise == "dwt_per":
			ext="per"
			[dwt_output,length,flag]=dwt.dwt(signal,J_dn,nm_dn,ext)
			dwt_len=int(len(dwt_output))
			dwt_med=np.abs(dwt_output)
			sigma=np.median(dwt_med)
			td=sqrt(2.0 * np.log(dwt_len)) * sigma / 0.6745
			
			if dn_thresh == "hard":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) <= td:
						dwt_output[iter]=0
						
			elif dn_thresh == "soft":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) >= td:
						dwt_output[iter]=np.sign(dwt_output[iter])*(np.abs(dwt_output[iter]) - td)
					else:
						dwt_output[iter]=0
			
			output=dwt.idwt(dwt_output,nm_dn,length,flag)			
			
		else:
			ext="sym"
			[dwt_output,length,flag]=dwt.dwt(signal,J_dn,nm_dn,ext)
			dwt_len=int(len(dwt_output))
			dwt_med=np.abs(dwt_output)
			sigma=np.median(dwt_med)
			td=sqrt(2.0 * np.log(dwt_len)) * sigma / 0.6745
			
			if dn_thresh == "hard":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) <= td:
						dwt_output[iter]=0
						
			elif dn_thresh == "soft":
				for iter in range(dwt_len):
					if np.abs(dwt_output[iter]) >= td:
						dwt_output[iter]=np.sign(dwt_output[iter])*(np.abs(dwt_output[iter]) - td)
					else:
						dwt_output[iter]=0
			
			output=dwt.idwt(dwt_output,nm_dn,length,flag)
			
	elif dn_method == "sureshrink" or dn_method == "sure":
		if mode_denoise == "swt":
			[dwt_output,length]=dwt.swt(signal,J_dn,nm_dn)
			for it in range(J_dn):
				dwt_med=np.abs(dwt_output[(it+1)*length:(it+2)*length])
				coef=(dwt_output[(it+1)*length:(it+2)*length])
				sigma=np.median(dwt_med)
				dwt_len=int(length)
				
				if sigma < 0.00000001:
					td=0
				else:
					tv=sqrt(2.0 * np.log(dwt_len))
					norm1=np.linalg.norm(coef)
					te=(norm1**2 - dwt_len)/dwt_len
					ct=((np.log(dwt_len)/np.log(2))**1.5)/sqrt(dwt_len)
					
					if te < ct:
						td = tv
					else:
						dwt_med=np.sort(dwt_med)
						dmlen=int(len(dwt_med))
						x_sure=dwt_med**2
						x_sum=np.sum(x_sure)
						
						risk_vector=(dmlen - (2 *(np.arange(dmlen)+1)) + x_sum + (x_sure * np.linspace(dmlen-1,0,dmlen)))/dmlen
						minindex = risk_vector.argmin()
						thr=sqrt(x_sure[minindex])
						td=min(thr,tv)
				
				td = td * sigma / 0.6745
				if dn_thresh == "hard":
					for iter in range(dwt_len):
						if dwt_med[iter] <= td:
							dwt_output[iter+(it+1)*length]=0
				
				elif dn_thresh == "soft":
					for iter in range(dwt_len):
						if dwt_med[iter] >= td:
							dwt_output[iter+(it+1)*length]=np.sign(dwt_output[iter+(it+1)*length])*(np.abs(dwt_output[iter+(it+1)*length]) - td)
						else:
							dwt_output[iter+(it+1)*length]=0
						
			output=dwt.iswt(dwt_output,J_dn,nm_dn)		
		
		elif mode_denoise == "per" or mode_denoise == "dwt_per":
			ext="per"
			[dwt_output,length,flag]=dwt.dwt(signal,J_dn,nm_dn,ext)
			len1=int(len(dwt_output)/2**J_dn)
			
			for it in range(J_dn):
				dwt_med=np.abs(dwt_output[len1:2*len1])
				coef=dwt_output[len1:2*len1]
				sigma=np.median(dwt_med)
				dwt_len=int(len1)
				
				if sigma < 0.00000001:
					td=0
				else:
					tv=sqrt(2.0 * np.log(dwt_len))
					norm1=np.linalg.norm(coef)
					te=(norm1**2 - dwt_len)/dwt_len
					ct=((np.log(dwt_len)/np.log(2))**1.5)/sqrt(dwt_len)
					
					if te < ct:
						td = tv
					else:
						dwt_med=np.sort(dwt_med)
						dmlen=int(len(dwt_med))
						x_sure=dwt_med**2
						x_sum=np.sum(x_sure)
						
						risk_vector=(dmlen - (2 *(np.arange(dmlen)+1)) + x_sum + (x_sure * np.linspace(dmlen-1,0,dmlen)))/dmlen
						minindex = risk_vector.argmin()
						thr=sqrt(x_sure[minindex])
						td=min(thr,tv)
				
				td = td * sigma / 0.6745
				
				if dn_thresh == "hard":
					for iter in range(dwt_len):
						if dwt_med[iter] <= td:
							dwt_output[iter+len1]=0
				
				elif dn_thresh == "soft":
					for iter in range(dwt_len):
						if dwt_med[iter] >= td:
							dwt_output[iter+len1]=np.sign(dwt_output[iter+len1])*(np.abs(dwt_output[iter+len1]) - td)
						else:
							dwt_output[iter+len1]=0
							
				
				len1=int(2*len1)
			
			output=dwt.idwt(dwt_output,nm_dn,length,flag)						
		
		else:
			ext="sym"
			[dwt_output,length,flag]=dwt.dwt(signal,J_dn,nm_dn,ext)
			len1=length[0]
			
			for it in range(J_dn):
				dwt_med=np.abs(dwt_output[len1:len1+length[it+1]])
				coef=dwt_output[len1:len1+length[it+1]]
				sigma=np.median(dwt_med)
				dwt_len=int(length[it+1])
				
				if sigma < 0.00000001:
					td=0
				else:
					tv=sqrt(2.0 * np.log(dwt_len))
					norm1=np.linalg.norm(coef)
					te=(norm1**2 - dwt_len)/dwt_len
					ct=((np.log(dwt_len)/np.log(2))**1.5)/sqrt(dwt_len)
					
					if te < ct:
						td = tv
					else:
						dwt_med=np.sort(dwt_med)
						dmlen=int(len(dwt_med))
						x_sure=dwt_med**2
						x_sum=np.sum(x_sure)
						
						risk_vector=(dmlen - (2 *(np.arange(dmlen)+1)) + x_sum + (x_sure * np.linspace(dmlen-1,0,dmlen)))/dmlen
						minindex = risk_vector.argmin()
						thr=sqrt(x_sure[minindex])
						td=min(thr,tv)
				
				td = td * sigma / 0.6745
				
				if dn_thresh == "hard":
					for iter in range(dwt_len):
						if dwt_med[iter] <= td:
							dwt_output[iter+len1]=0
				
				elif dn_thresh == "soft":
					for iter in range(dwt_len):
						if dwt_med[iter] >= td:
							dwt_output[iter+len1]=np.sign(dwt_output[iter+len1])*(np.abs(dwt_output[iter+len1]) - td)
						else:
							dwt_output[iter+len1]=0
							
				
				len1=len1+length[it+1]
			
			output=dwt.idwt(dwt_output,nm_dn,length,flag)
																
	return output
	
"""def main():
	x=np.array([])
	J_dn=2
	nm_dn='sym4'
	input=open('noisybumps.txt','r')
	for file in input:
		x=np.append(x,float(file))
	
	input.close()
	import matplotlib as mpl
	import matplotlib.pyplot as plt
	plt.subplot(2,1,1)
	plt.plot(x)
	plot.ylabel('Noisy Signal')
	mode_denoise='swt'
	dn_method='visushrink'
	dn_thresh='soft'
	out=denoise(x,mode_denoise,nm_dn,J_dn,dn_method,dn_thresh)
	
	plt.subplot(2,1,2)
	plt.plot(out)
	plt.ylabel('DeNoised')
	plt.draw()
	plt.show()


if __name__ == '__main__':
	main()		
					"""	
					
				
			
			
			
	
	
		
	
		
	
	
	
