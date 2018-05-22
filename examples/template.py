#Template for maniupulating Nbody Star Cluster simulations
import nbodypy as npy
import sys,os

#Set files to read in simulation
filepath=''
bfilename='fort.82'
sfilename='fort.83'

#If not in current directory, check for a /start directory
if not os.path.isfile(sfilename):
    filepath+='./start/'

#Open files
f82=open(filepath+bfilename,'r')
f83=open(filepath+sfilename,'r')

#Get first snapshot
#Can edit whether or not key_params should be calculated and if units should be converted
cluster=npy.get_nbody6_jarrod(f82,f83,do_keyparams=True)
npy.nbody_to_realpc(cluster)

#Loop through all timesteps and/or to a specific timestep
while cluster.ntot>0.0 and cluster.tphys<=12000.0:
    print(cluster.tphys,cluster.ntot)
    #OPERATE ON TIMESTEP HERE*************************************
    
    
    
    #Read in next timestep****************************************
    cluster=npy.get_nbody6_jarrod(f82,f83,do_keyparams=False)
    npy.nbody_to_realpc(cluster)

    #Check for restart directory
    if cluster.ntot==0:
        f82.close()
        f83.close()
        filepath+='cont/'
        if os.path.isfile(filepath+sfilename):
            f82=open(filepath+bfilename,'r')
            f83=open(filepath+sfilename,'r')
            cluster=npy.get_nbody6_jarrod(f82,f83,do_keyparams=True)
            npy.nbody_to_realpc(cluster)
