#! /usr/bin/env python

import sys
import numpy as np
import filter,misc,convol,sample

def swt2(inpsig,J,nm):
    swtout=np.array([])
    sig=np.array(inpsig)
    m_size=int(np.size(sig,0))
    n_size=int(np.size(sig,1))
    rows_n=m_size
    cols_n=n_size
    [lp1,hp1,lp2,hp2]=filter.filtcoef(nm)
    
    for iter in range(J):
        U=int(2**iter)
        low_pass=np.array([])
        high_pass=np.array([])
        if iter>0:
            low_pass=sample.upsamp(lp1,U)
            high_pass=sample.upsamp(hp1,U)
        else:
            low_pass=lp1
            high_pass=hp1
        
        lf=int(len(low_pass))
        
        if int(np.size(sig,0)%2) == 0:
            rows_n=int(np.size(sig,0))
        else:
            rows_n=int(np.size(sig,0)+1)           
        
        if int(np.size(sig,1)%2) == 0:
            cols_n=int(np.size(sig,1))
        else:
            cols_n=int(np.size(sig,1)+1) 
        
        
        
        signal=np.ndarray(shape=(rows_n+lf,cols_n+lf))
        
        signal=misc.per_ext2d(sig,lf/2)
        len_x=int(np.size(signal,0))
        len_y=int(np.size(signal,1))
     
        sigL=np.ndarray(shape=(rows_n+lf,cols_n))
        sigH=np.ndarray(shape=(rows_n+lf,cols_n))
        cA=np.ndarray(shape=(rows_n,cols_n))
        cH=np.ndarray(shape=(rows_n,cols_n))
        cV=np.ndarray(shape=(rows_n,cols_n))
        cD=np.ndarray(shape=(rows_n,cols_n))
        
        for i in range(len_x):
            temp_row=signal[i,0:len_y]
            oup=np.real(convol.convfft(temp_row,low_pass))
            oup=oup[lf:]
            oup=oup[0:cols_n]
            
            oup2=np.real(convol.convfft(temp_row,high_pass))
            oup2=oup2[lf:]
            oup2=oup2[0:cols_n]
            
            sigL[i,:]=oup
            sigH[i,:]=oup2
        
        for j in range(cols_n):
            temp_row=sigL[0:len_x,j]
            oup=np.real(convol.convfft(temp_row,low_pass))
            oup=oup[lf:]
            oup=oup[0:rows_n]
            
            oup2=np.real(convol.convfft(temp_row,high_pass))
            oup2=oup2[lf:]
            oup2=oup2[0:rows_n]
            
            cA[:,j]=oup
            cH[:,j]=oup2
            
        
        for j in range(cols_n):
            temp_row=sigH[0:len_x,j]
            oup=np.real(convol.convfft(temp_row,low_pass))
            oup=oup[lf:]
            oup=oup[0:rows_n]
            
            oup2=np.real(convol.convfft(temp_row,high_pass))
            oup2=oup2[lf:]
            oup2=oup2[0:rows_n]
            
            cV[:,j]=oup
            cD[:,j]=oup2
        
        sig=cA
        temp_sig2=np.array([])
        if iter==J-1:
            temp_sig2=np.reshape(cA,[np.size(cA,0)*np.size(cA,1)])
        
        temp=np.reshape(cH,[np.size(cH,0)*np.size(cH,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        temp=np.reshape(cV,[np.size(cV,0)*np.size(cV,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        temp=np.reshape(cD,[np.size(cD,0)*np.size(cD,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        
        swtout=np.concatenate([temp_sig2,swtout])
                
    length=np.array([rows_n,cols_n])            
    return swtout,length    
    
    

def dispdwt(output,length,J):
    length2=out_dim(length,J)
    sz=len(length2)
    rows_ds=length2[sz-2]
    cols_ds=length2[sz-1]
    dwtdisp=np.ndarray(shape=(rows_ds,cols_ds))
    sum=int(0)
    
    for iter in range(J):
        d_rows=int(length[2*iter]-length2[2*iter])
        d_cols=int(length[2*iter+1]-length2[2*iter+1])
        
        rows_n=int(length[2*iter])
        cols_n=int(length[2*iter+1])
        dwt_output=np.ndarray(shape=(2*rows_n,2*cols_n))
        
        if iter==0:
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i,j]=output[i*cols_n+j]
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i,j+cols_n]=output[rows_n*cols_n+i*cols_n+j]
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i+rows_n,j]=output[2*rows_n*cols_n+i*cols_n+j]
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i+rows_n,j+cols_n]=output[3*rows_n*cols_n+i*cols_n+j]
            
        else:
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i,j+cols_n]=output[sum+i*cols_n+j]
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i+rows_n,j]=output[sum+rows_n*cols_n+i*cols_n+j]
            
            for i in range(rows_n):
                for j in range(cols_n):
                    dwt_output[i+rows_n,j+cols_n]=output[sum+2*rows_n*cols_n+i*cols_n+j]
            
        
        rows_x=int(length2[2*iter])
        cols_x=int(length2[2*iter+1])
        
        d_cols2=int(np.ceil((d_cols-1)*1.0/2.0))
        d_rows2=int(np.ceil((d_rows-1)*1.0/2.0))
        
        if iter==0:
            for i in range(rows_x):
                for j in range(cols_x):
                    if i+d_rows-1<0:
                        dwtdisp[i,j]=0
                    elif j+d_cols-1<0:
                        dwtdisp[i,j]=0
                    else:
                        dwtdisp[i,j]=dwt_output[i+d_rows-1,j+d_cols-1]
                    
        for i in range(rows_x):
            for j in range(cols_x):
                if i+d_rows2<0:
                    dwtdisp[i,j+cols_x]=0
                elif j+cols_x+2*d_cols-1>np.size(dwt_output,1)-1:
                    dwtdisp[i,j+cols_x]=0
                else:
                    dwtdisp[i,j+cols_x]=dwt_output[i+d_rows2,j+cols_x+2*d_cols-1]
            
        for i in range(rows_x):
                for j in range(cols_x):
                    if i+rows_x+2*d_rows-1>np.size(dwt_output,0)-1:
                        dwtdisp[i+rows_x,j]=0
                    elif j+d_cols2<0:
                        dwtdisp[i+rows_x,j]=0
                    else:
                        dwtdisp[i+rows_x,j]=dwt_output[i+rows_x+2*d_rows-1,j+d_cols2]                
        
        for i in range(rows_x):
                for j in range(cols_x):
                    if i+rows_x+d_rows+d_rows2>np.size(dwt_output,0)-1:
                        dwtdisp[i+rows_x,j+cols_x]=0
                    elif j+cols_x+d_cols+d_cols2>np.size(dwt_output,1)-1:
                        dwtdisp[i+rows_x,j+cols_x]=0
                    else:
                        dwtdisp[i+rows_x,j+cols_x]=dwt_output[i+rows_x+d_rows+d_rows2,j+cols_x+d_cols+d_cols2]
                    
                    
        if iter==0:
            sum+=4*rows_n*cols_n
        else:
            sum+=3*rows_n*cols_n
    
    return dwtdisp
        
        

def out_dim(length,J):
    sz=len(length)
    rows=length[sz-2]
    cols=length[sz-1]
    
    for i in range(J):
        rows=int(np.ceil(rows*1.0/2.0))
        cols=int(np.ceil(cols*1.0/2.0))
        
    length2=np.array([])
    
    for i in range(J+1):
        length2=np.append(length2,rows)
        length2=np.append(length2,cols)
        rows=int(rows*2)
        cols=int(cols*2)
    
    return length2
        

def idwt2(dwtop,nm,length,flag):
    J=int(flag[0])
    rows=int(length[0])
    cols=int(length[1])
    sum_coef=int(0)
    [lp1,hp1,lp2,hp2]=filter.filtcoef(nm)
    lf=len(lp1)
    
    for iter in range(J):
        rows_n=int(length[2*int(iter)])
        cols_n=int(length[2*int(iter)+1])
        
        if iter==0:
            temp=dwtop[0:cols_n*rows_n]
            cLL=np.reshape(temp,[rows_n,cols_n])
            temp=dwtop[cols_n*rows_n:2*cols_n*rows_n]
            cLH=np.reshape(temp,[rows_n,cols_n])
            temp=dwtop[2*cols_n*rows_n:3*cols_n*rows_n]
            cHL=np.reshape(temp,[rows_n,cols_n])
            temp=dwtop[3*cols_n*rows_n:4*cols_n*rows_n]
            cHH=np.reshape(temp,[rows_n,cols_n])
        else:
            temp=dwtop[sum_coef:sum_coef+rows_n*cols_n]
            cLH=np.reshape(temp,[rows_n,cols_n])
            temp=dwtop[sum_coef+rows_n*cols_n:sum_coef+2*rows_n*cols_n]
            cHL=np.reshape(temp,[rows_n,cols_n])
            temp=dwtop[sum_coef+2*rows_n*cols_n:sum_coef+3*rows_n*cols_n]
            cHH=np.reshape(temp,[rows_n,cols_n])
        
        len_x=np.size(cLH,0)
        len_y=np.size(cLH,1)
        
        if flag[2]==0:
            cL=np.ndarray(shape=(2*len_x,len_y))
            cH=np.ndarray(shape=(2*len_x,len_y))
            t_iter=2*len_x
        else:
            cL=np.ndarray(shape=(2*len_x-lf+2,len_y))
            cH=np.ndarray(shape=(2*len_x-lf+2,len_y))
            t_iter=2*len_x-lf+2
        
        if iter==0:
            for j in range(len_y):
                sigLL=cLL[0:len_x,j]
                sigLH=cLH[0:len_x,j]
                if int(flag[2])==0:
                    oup=idwt1(sigLL,sigLH,nm)
                    cL[:,j]=oup
                else:
                    oup=idwt1_sym(sigLL,sigLH,nm)
                    cL[:,j]=oup
                    
        else:
            rows1=int(np.size(cLH,0))
            cols1=int(np.size(cLH,1))
            
            for j in range(cols1):
                sigLL=cLL[0:rows1,j]
                sigLH=cLH[0:rows1,j]
                if int(flag[2])==0:
                    oup=idwt1(sigLL,sigLH,nm)
                    cL[:,j]=oup
                else:
                    oup=idwt1_sym(sigLL,sigLH,nm)
                    cL[:,j]=oup    
        
        for j in range(len_y):
            sigHL=cHL[0:len_x,j]
            sigHH=cHH[0:len_x,j]
            if int(flag[2])==0:
                oup=idwt1(sigHL,sigHH,nm)
                cH[:,j]=oup
            else:
                oup=idwt1_sym(sigHL,sigHH,nm)
                cH[:,j]=oup    
        
        if int(flag[2])==0:
            signal=np.ndarray(shape=(2*len_x,2*len_y))
        else:
            signal=np.ndarray(shape=(2*len_x-lf+2,2*len_y-lf+2))
        
        for i in range(t_iter):
            sigL=cL[i,0:len_y]
            sigH=cH[i,0:len_y]
            if int(flag[2])==0:
                oup=idwt1(sigL,sigH,nm)
                signal[i,:]=oup
            else:
                oup=idwt1_sym(sigL,sigH,nm)
                signal[i,:]=oup    
        
        idwt_output=signal
        if iter==0:
            sum_coef+=4*rows_n*cols_n
        else:
            sum_coef+=3*rows_n*cols_n
        
        cLL=signal
    
    len_length=int(len(length))
    idwt_output=idwt_output[0:int(length[len_length-2]),0:int(length[len_length-1])]
    return idwt_output
            
                
        
def dwt2_sym(signal,name):
    rows=int(np.size(signal,0))
    cols=int(np.size(signal,1))
    [lp1,hp1,lp2,hp2]=filter.filtcoef(name)
    lf=len(lp1)
    rows_n=int(np.floor((rows+lf-1)*1.0/2.0))
    cols_n=int(np.floor((cols+lf-1)*1.0/2.0))
    
    lp_dn1=np.ndarray(shape=(rows,cols_n))
    hp_dn1=np.ndarray(shape=(rows,cols_n))
    cLL=np.ndarray(shape=(rows_n,cols_n))
    cLH=np.ndarray(shape=(rows_n,cols_n))
    cHL=np.ndarray(shape=(rows_n,cols_n))
    cHH=np.ndarray(shape=(rows_n,cols_n))
    
    
    for i in range(rows):
        temp_row=signal[i,:]
        [oup_lp,oup_hp]=dwt1_sym(temp_row,name)
        lp_dn1[i,:]=oup_lp
        hp_dn1[i,:]=oup_hp
    
    cols=cols_n
    
    for j in range(cols):
        temp_row3=lp_dn1[:,j]
        [oup_lp,oup_hp]=dwt1_sym(temp_row3,name)
        cLL[:,j]=oup_lp
        cLH[:,j]=oup_hp
        
    for j in range(cols):
        temp_row5=hp_dn1[:,j]
        [oup_lp,oup_hp]=dwt1_sym(temp_row5,name)
        cHL[:,j]=oup_lp
        cHH[:,j]=oup_hp
    
    return cLL,cLH,cHL,cHH        

def dwt2_per(signal,name):
    rows=int(np.size(signal,0))
    cols=int(np.size(signal,1))
    rows_n=int(np.ceil(rows*1.0/2.0))
    cols_n=int(np.ceil(cols*1.0/2.0))
    
    lp_dn1=np.ndarray(shape=(rows,cols_n))
    hp_dn1=np.ndarray(shape=(rows,cols_n))
    cLL=np.ndarray(shape=(rows_n,cols_n))
    cLH=np.ndarray(shape=(rows_n,cols_n))
    cHL=np.ndarray(shape=(rows_n,cols_n))
    cHH=np.ndarray(shape=(rows_n,cols_n))
    
    [lp1,hp1,lp2,hp2]=filter.filtcoef(name)
    
    for i in range(rows):
        temp_row=signal[i,:]
        [oup_lp,oup_hp]=dwt1(temp_row,name)
        lp_dn1[i,:]=oup_lp
        hp_dn1[i,:]=oup_hp
    
    cols=cols_n
    
    for j in range(cols):
        temp_row3=lp_dn1[:,j]
        [oup_lp,oup_hp]=dwt1(temp_row3,name)
        cLL[:,j]=oup_lp
        cLH[:,j]=oup_hp
        
    for j in range(cols):
        temp_row5=hp_dn1[:,j]
        [oup_lp,oup_hp]=dwt1(temp_row5,name)
        cHL[:,j]=oup_lp
        cHH[:,j]=oup_hp
    
    return cLL,cLH,cHL,cHH
    

def dwt2(signal,J,nm,ext):
    flag=np.array([])
    dwtout=np.array([])
    length=np.array([])
    sig=np.array(signal)
    rows_n=int(np.size(sig,0))
    cols_n=int(np.size(sig,1))
    Max_Iter=min(int(np.ceil(np.log2(rows_n))),int(np.ceil(np.log2(cols_n))))
    if Max_Iter < J:
        print J," Iterations are not possible with signals of this dimension "
    
    flag=np.append(flag,J)
    flag=np.append(flag,0)
    if ext == 'per':
        flag=np.append(flag,int(0))
    else:
        flag=np.append(flag,int(1))
    
    length=np.append(int(cols_n),length)
    length=np.append(int(rows_n),length)
    
    orig=sig;
    [lp1,hp1,lp2,hp2]=filter.filtcoef(nm)
    lf=len(lp1)
    for iter in range(J):
        if ext=='per':
            rows_n=int(np.ceil(rows_n*1.0/2.0))
            cols_n=int(np.ceil(cols_n*1.0/2.0))
        else:
            rows_n=int(np.floor((rows_n+lf-1)*1.0/2.0))
            cols_n=int(np.floor((cols_n+lf-1)*1.0/2.0))
            
        length=np.append(int(cols_n),length)
        length=np.append(int(rows_n),length)
        
        if ext=='per':
            [cA,cH,cV,cD]=dwt2_per(orig,nm)
        else:
            [cA,cH,cV,cD]=dwt2_sym(orig,nm)
        temp_sig2=np.array([])
        
        orig=cA
        
        if iter==J-1:
            temp_sig2=np.reshape(cA,[np.size(cA,0)*np.size(cA,1)])
        
        temp=np.reshape(cH,[np.size(cH,0)*np.size(cH,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        temp=np.reshape(cV,[np.size(cV,0)*np.size(cV,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        temp=np.reshape(cD,[np.size(cD,0)*np.size(cD,1)])
        temp_sig2=np.concatenate([temp_sig2,temp])
        
        dwtout=np.concatenate([temp_sig2,dwtout])
        
                
    
    return dwtout,length,flag
    
    

def iswt(swtop,J,nm):
    N=int(len(swtop)/(J+1))
    [lpd,hpd,lpr,hpr]=filter.filtcoef(nm)
    low_pass=lpr
    high_pass=hpr
    lf=int(len(low_pass))
    
    for iter in range(J):
        iswt_output=np.zeros(N)
        
        if iter==0:
            appx_sig=swtop[0:N]
            det_sig=swtop[N:2*N]
        else:
            det_sig=swtop[(iter+1)*N:(iter+2)*N]
        
        value=int(2**(J-1-iter))
        for count in range(value):
            appx1=appx_sig[count:N:value]
            det1=det_sig[count:N:value]
            
            len1=len(appx1)
            
            appx2=appx1[0:len1:2]
            det2=det1[0:len1:2]
            
            U=int(2)
            
            cL0=sample.upsamp(appx2,U)
            cH0=sample.upsamp(det2,U)
            
            cL0=misc.per_ext(cL0,int(lf/2))
            cH0=misc.per_ext(cH0,int(lf/2))
            
            oup00L=np.real(convol.convfft(cL0,low_pass))
            oup00H=np.real(convol.convfft(cH0,high_pass))
            
            oup00L=oup00L[lf-1:]
            oup00L=oup00L[0:len1]
            
            oup00H=oup00H[lf-1:]
            oup00H=oup00H[0:len1]
            
            oup00=oup00L+oup00H
            
            appx3=appx1[1:len1:2]
            det3=det1[1:len1:2]
            
            cL1=sample.upsamp(appx3,U)
            cH1=sample.upsamp(det3,U)
            
            cL1=misc.per_ext(cL1,int(lf/2))
            cH1=misc.per_ext(cH1,int(lf/2))
            
            oup01L=np.real(convol.convfft(cL1,low_pass))
            oup01H=np.real(convol.convfft(cH1,high_pass))
            
            oup01L=oup01L[lf-1:]
            oup01L=oup01L[0:len1]
            
            oup01H=oup01H[lf-1:]
            oup01H=oup01H[0:len1]
            
            oup01=oup01L+oup01H
            
            oup01=misc.circshift(oup01,-1)
            index2=int(0)
            for index in xrange(count,N,value):
                temp=(oup00[index2]+oup01[index2])*1.0/2.0
                iswt_output[index]=temp
                index2+=1
            
        appx_sig=iswt_output
    
    return iswt_output
                
            
            
            

def swt(sig,J,nm):
    swtop=np.array([])
    N=int(len(sig))
    length=N
    
    [lpd,hpd,lpr,hpr]=filter.filtcoef(nm)
    
    for iter in range(J):
        if iter > 0:
            M=int(2**iter)
            low_pass=sample.upsamp(lpd,M)
            high_pass=sample.upsamp(hpd,M)
        else:
            low_pass=lpd
            high_pass=hpd
            
        len_filt=int(len(low_pass))    
        sig=misc.per_ext(sig,int(len_filt/2))
        cA=np.real(convol.convfft(sig,low_pass))
        cD=np.real(convol.convfft(sig,high_pass))
        
        cA=cA[len_filt:]
        cA=cA[0:N]
        
        cD=cD[len_filt:]
        cD=cD[0:N]
        
        sig=cA
        if iter==J-1:
            swtop=np.append(cD,swtop)
            swtop=np.append(cA,swtop)
        else:
            swtop=np.append(cD,swtop)
        
    
    return swtop,length
            

def idwt1_sym(cA,cD,wname):
    [lpd1,hpd1,lpr1,hpr1]=filter.filtcoef(wname)
    if len(cA) > len(cD):
        cA=cA[0:len(cD)]
        
    len_lpfilt=int(len(lpr1))
    len_hpfilt=int(len(hpr1))
    lf=len_lpfilt
    N= 2 * len(cD)
    U=2

    cA_up=sample.upsamp(cA,U)
    cA_up=cA_up[0:len(cA_up)-1]
    X_lp=np.real(convol.convfft(cA_up,lpr1))

    cD_up=sample.upsamp(cD,U)
    cD_up=cD_up[0:len(cD_up)-1]
    X_hp=np.real(convol.convfft(cD_up,hpr1))
    
    X=X_lp+X_hp
    X=X[lf-2:]
    X=X[:len(X)-lf+2]
    
    return X

def idwt1(cA,cD,wname):
    [lpd1,hpd1,lpr1,hpr1]=filter.filtcoef(wname)

    len_lpfilt=int(len(lpr1))
    len_hpfilt=int(len(hpr1))
    len_avg=int(len_lpfilt/2 + len_hpfilt/2)
    N= 2 * len(cD)
    U=2

    cA_up=sample.upsamp(cA,U)
    cA_up=misc.per_ext(cA_up,int(len_avg/2))
    X_lp=np.real(convol.convfft(cA_up,lpr1))

    cD_up=sample.upsamp(cD,U)
    cD_up=misc.per_ext(cD_up,int(len_avg/2))
    X_hp=np.real(convol.convfft(cD_up,hpr1))
    
    X_lp=X_lp[0:N+len_avg-1]
    X_lp=X_lp[len_avg-1:]

    X_hp=X_hp[0:N+len_avg-1]
    X_hp=X_hp[len_avg-1:]
    
    X=X_lp+X_hp
    return X

def idwt(dwtop,nm,length,flag):

    J=int(flag[1])
    app_len=int(length[0])
    det_len=int(length[1])
    app=dwtop[0:app_len]
    det=dwtop[app_len:2*app_len]

    for i in range(J):
        if int(flag[2]) == 0:
            idwt_output=idwt1(app,det,nm)
        else:
            idwt_output=idwt1_sym(app,det,nm)
            
        app_len+=det_len

        if i < J-1:
            det_len=length[i+2]
            det=dwtop[app_len:app_len+det_len]
            app=idwt_output

            if len(app) > len(det):
                t=len(app)-len(det)
                lent=int(np.floor(t * 1.0/2.0))
                app=app[:lent+len(det)]
                app=app[lent:]
    
    zerp=int(flag[0])
    idwt_output=idwt_output[0:len(idwt_output)-zerp]
    return idwt_output

def dwt1_sym(signal,wname):
    [lpd,hpd,lpr,hpr]=filter.filtcoef(wname)
    len_lpfilt=int(len(lpd))
    len_hpfilt=int(len(hpd))
    lf=len_lpfilt
    D=int(2)

    signal=misc.symm_ext(signal,int(lf - 1))
   

    cA_undec=np.real(convol.convfft(signal,lpd))
    cA_undec=cA_undec[lf:]
    cA_undec=cA_undec[:len(cA_undec)-lf+1]
    cA=sample.downsamp(cA_undec,D)


    cD_undec=np.real(convol.convfft(signal,hpd))
    cD_undec=cD_undec[lf:]
    cD_undec=cD_undec[:len(cD_undec)-lf+1]
    cD=sample.downsamp(cD_undec,D)

    return cA,cD

def dwt1(signal,wname):
    [lpd,hpd,lpr,hpr]=filter.filtcoef(wname)
    len_lpfilt=int(len(lpd))
    len_hpfilt=int(len(hpd))
    len_avg=int(len_lpfilt/2 + len_hpfilt/2)
    len_sig = int( 2 *(np.ceil(len(signal) * 1.0/2.0)))
    D=int(2)

    signal=misc.per_ext(signal,int(len_avg/2))
   

    cA_undec=np.real(convol.convfft(signal,lpd))
    cA_undec=cA_undec[len_avg-1:]
    cA_undec=cA_undec[:len(cA_undec)-len_avg+1]
    cA_undec=cA_undec[1:len_sig]
    cA=sample.downsamp(cA_undec,D)


    cD_undec=np.real(convol.convfft(signal,hpd))
    cD_undec=cD_undec[len_avg-1:]
    cD_undec=cD_undec[:len(cD_undec)-len_avg+1]
    cD_undec=cD_undec[1:len_sig]
    cD=sample.downsamp(cD_undec,D)

    return cA,cD




def dwt(sig,J,nm,ext):
    flag=np.array([])
    dwtout=np.array([])
    length=np.array([])
    Max_Iter=int(np.ceil(np.log2(len(sig))))-2
    if Max_Iter < J:
        J=Max_Iter
    
    temp_len=len(sig)

    if temp_len%2 != 0:
        temp=sig[temp_len-1]
        sig=np.append(sig,temp)
        flag=np.append(flag,1)
        temp_len+=1

    else:
        flag=np.append(flag,0)

    length=np.append(length,int(temp_len))
    flag=np.append(flag,J)
    if ext == 'per':
        flag=np.append(flag,int(0))
    else:
        flag=np.append(flag,int(1))
        
    orig=sig

    for iter in range(J):
        if ext == 'per':
            [appx,det]=dwt1(orig,nm)
        else:
            [appx,det]=dwt1_sym(orig,nm)
        dwtout=np.append(det,dwtout)
        l_temp=int(len(det))
        length=np.append(l_temp,length)
        if iter==J-1:
            dwtout=np.append(appx,dwtout)
            l_temp2=int(len(appx))
            length=np.append(l_temp2,length)

        orig=appx



    return dwtout,length,flag

"""def main():
    x=np.arange(400)
    x=np.reshape(x,[20,20])
    nm='db1'
    J=1
    [a,b]=swt2(x,J,nm)
    
    print len(a)
    
    for i in b:
        print i
    

if __name__ == '__main__':
    main()"""
    

        


