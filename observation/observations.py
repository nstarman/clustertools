#Routines for analysing Nbody models as if they were Observations
import numpy as np

def obsrbinmaker(r,rm,obs_mask):
    """
    NAME:

       obsrbinmaker (WORK IN PROGRESS)

    PURPOSE:

       Radially bin data based on a set of observations
       --> Want to include spatial and magnitude/mass cuts 

    INPUT:

       r - stellar radii

       rm - cluster half-mass radius

       obs_mask - name of observational mask to be placed on cluster (Only current working mask is M30)

    OUTPUT:

       r_lower,r_mean,r_upper,r_hist

    HISTORY:

       2018 - Written - Webb (UofT)
    """

    if obs_mask=='M30':
        rh=61.800000000000004
        #In arcseconds:
        r_lower=np.array([10.0,20.0,40.0,200.0,250.0,350.0,650.0])
        r_upper=np.array([20.0,40.0,100.0,250.0,350.0,650.0,1000.0])

        r_lower=rm*r_lower/rh
        r_upper=rm*r_upper/rh

        r_hist=np.zeros(len(r_lower))
        r_sum=np.zeros(len(r_lower))

        for j in range(0,len(r_lower)):
            indx=(r>=r_lower[j]) * (r<=r_upper[j])
            r_hist[j]=len(r[indx])
            r_sum[j]=np.sum(r[indx])

        r_mean=[]
        for i in range(0,len(r_lower)):
            if r_hist[i]>0:
                r_mean=np.append(r_mean,r_sum[i]/r_hist[i])
            else:
                r_mean=np.append(r_mean,(r_lower[i]+r_upper[i])/2.0)

    return r_lower,r_mean,r_upper,r_hist
