""" The StarCluster class and key internal functions

"""

__author__ = "Jeremy J Webb"

__all__ = [
    'StarCluster',
    'sub_cluster'
]

import numpy as np
from galpy.util import bovy_conversion, bovy_coords
from textwrap import dedent
from galpy.potential import MWPotential2014
from .orbit import initialize_orbit, calc_actions
from .functions import *
from .profiles import *
from .operations import *
from .tails import *
from copy import copy

class StarCluster(object):
    """ A class that represents a star cluster population that ooperations and functions can be performed on
    
    Parameters
    ----------
    tphys : float
        Time (units not necessary) associated with the population (default: 0)
    units : str
        Units of stellar positions and velocties. Options include 'pckms',
        'kpckms','radec','nbody',and 'galpy'. For 'pckms' and 'kpckms', 
        stellar velocities are assumed to be km/s. (default: None)
    origin : str
        Origin of coordinate system within which stellar positions and velocities are defined. 
        Options include 'centre', 'cluster', 'galaxy' and 'sky'. Note that 'centre' corresponds
        to the systems centre of density or mass (as calculated by clustertools) while 'cluster' corresponds
        to the orbital position of the cluster's initial centre of mass given 'tphys'. In some cases
        these two coordinate systems may be the same. (default: None)
    ctype : str
        Code type used to generate the cluster population. Current options include 'snapshot',
        'nbody6','nbody6se','gyrfalcon','snaptrim', amuse','clustertools','snapauto'. The parameter
        informs clustertools how to load the stellar popuation and advance to the next snapshot.
        (default: 'snapshot')
    projected : bool
        return projected values instead of 3D value. (default: False)

    Returns
    -------
    StarCluster

    Other Parameters
    ---------------------------
    sfile : str
        name of file containing single star data
    bfile : str
        name of file contain binary star data
    ofilename : str
        orbit filename if ofile is not given
    ounits : str
        {'pckms','kpckms','radec','nbody','galpy'} units of orbital information (else assumed equal to StarCluster.units)
    nsnap : int
        if a specific snapshot is to be read in instead of starting from zero
    nzfill : int
        value for zfill when reading and writing snapshots (default: 5)
    snapbase : str
        string of characters in filename before nsnap (default: '')
    snapend : str
        string of character in filename after nsnap (default: '.dat')
    snapdir : str
        string name of directory of snapshots if different than wdir (Default: '')
    delimiter : str 
        choice of delimiter when reading ascii/csv files (default: ',')
    wdir : str
        working directory of snapshots if not current directory
    intialize : bool
        initialize a galpy orbit after reading in orbital information (default: False)
    advance : bool
        set to True if this a snapshot that has been advanced to from an initial one? (default: False)
    centre_method: str
        {None,'orthographic','VandeVen'} method to convert to clustercentric coordinates when units are in radec (Default: None)

    History
    -------
    2018 - Written - Webb (UofT)
    """
    def __init__(
        self, ntot=0, tphys=0.0, units=None, origin=None, ctype="snapshot", projected=False, **kwargs
    ):

        # Age of cluster
        self.tphys = tphys


        #Units and origin
        self.units = units
        self.origin = origin

        # Cluster Simulation Type
        self.ctype = ctype

        #Return projected values only
        self.projected=projected

        # Kwargs
        self.nsnap = int(kwargs.get("nsnap", "0"))
        self.delimiter = kwargs.get("delimiter", None)
        self.wdir = kwargs.get("wdir", "./")
        self.nzfill = int(kwargs.get("nzfill", "5"))
        self.snapbase = kwargs.get("snapbase", "")
        self.snapend = kwargs.get("snapend", ".dat")
        self.snapdir = kwargs.get("snapdir", "")
        self.skiprows = kwargs.get("skiprows", 0)
        self.sfile = kwargs.get("sfile", "")
        self.bfile = kwargs.get("bfile", "")
        self.projected = kwargs.get("projected", True)
        self.centre_method = kwargs.get("centre_method", None)

        # Total Number of Stars + Binaries in the cluster
        self.ntot = 0
        self.nb = 0

        # variables for add_stars
        self.id = np.array([])
        self.m = np.array([])
        self.x = np.array([])
        self.y = np.array([])
        self.z = np.array([])
        self.vx = np.array([])
        self.vy = np.array([])
        self.vz = np.array([])
        self.kw = np.array([])

        # variables for add_nbody
        self.zmbar = 1.0
        self.rbar = 1.0
        self.vstar = 1.0
        self.tstar = 1.0


        # variables for centre of cluster
        self.xc = 0.0
        self.yc = 0.0
        self.zc = 0.0
        self.vxc = 0.0
        self.vyc = 0.0
        self.vzc = 0.0

        # variables for orbital position and kinematics
        self.xgc = 0.0
        self.ygc = 0.0
        self.zgc = 0.0
        self.vxgc = 0.0
        self.vygc = 0.0
        self.vzgc = 0.0


        # variable for cluster's on-sky coordinates
        self.ra = np.array([])
        self.dec = np.array([])
        self.dist = np.array([])
        self.pmra = np.array([])
        self.pmdec = np.array([])
        self.vlos = np.array([])

        self.ra_gc = 0.0
        self.dec_gc = 0.0
        self.dist_gc = 0.0
        self.pmra_gc = 0.0
        self.pmdec_gc = 0.0
        self.vlos_gc = 0.0

        # variable for galpy orbit
        self.orbit = None
        self.orbits= None

        # variables for add_nbody6
        # Number of stars in the core
        self.nc = 0
        # Core radius
        self.rc = 0
        # Distance scaling parameter
        self.rbar = 1.
        # Tidal limit from NBODY6 (not neccesarily a true tidal radius)
        self.rtide = 0.
        # Center of mass of cluster (x,yz)
        self.xc = 0.
        self.yc = 0.
        self.zc = 0.
        # Mass scaling parameter
        self.zmbar = 1.
        # Velocity scaling parameter
        self.vstar = 1.
        # Scale radius of cluster
        self.rscale = 1.
        # Number of single stars
        self.ns = 0
        # Number of binary stars
        self.nb = 0
        # Number of particles (from NBODY6 when tidal tail is being integrated)
        self.np = 0

        # variables for add_sse (stellar evolution information)
        self.logl = np.asarray([])
        self.logr = np.asarray([])
        self.lum = np.asarray([])
        self.ep = np.asarray([])
        self.ospin = np.asarray([])

        # variables for add_bse (binary star evolution information)
        self.id1 = np.asarray([])
        self.id2 = np.asarray([])
        self.kw1 = np.asarray([])
        self.kw2 = np.asarray([])
        self.kcm = np.asarray([])
        self.ecc = np.asarray([])
        self.pb = np.asarray([])
        self.semi = np.asarray([])
        self.m1 = np.asarray([])
        self.m2 = np.asarray([])
        self.logl1 = np.asarray([])
        self.logl2 = np.asarray([])
        self.logr1 = np.asarray([])
        self.logr2 = np.asarray([])
        self.ep1 = np.asarray([])
        self.ep2 = np.asarray([])
        self.ospin1 = np.asarray([])
        self.ospin2 = np.asarray([])

        # variables of energies
        self.kin = np.asarray([])
        self.pot = np.asarray([])
        self.etot = np.asarray([])

        # Lagrange Radii,10% lagrage radius, half-mass radius, limiting radius, tidal radius, and virial radius
        self.rn = None
        self.r10 = None
        self.rm = None
        self.rl = None
        self.rt = None
        self.rv = None

        #3D and projected order of stars with respect to origin
        self.rorder = None
        self.rproorder = None

        # Additional variables for operation and function calls
        self.trelax = None
        self.trh = None
        self.trc = None
        self.qv = None
        self.alpha = None
        self.eta = None

    def add_stars(
        self, x, y, z, vx, vy, vz,m=None,id=None,do_key_params=False, do_order=False
    ):
        """add stars to StarCluster

        Parameters
        ----------

        x,y,z: float
            stellar positions. Input is assumed to be in cartesian coordinates unless self.units=='radec' 
            and self.origin=='sky', then positions are assumed to be ra,dec,dist (degrees, degrees, kpc)
        vx,vy,vz: float
            atellar velocities. Input is assumed to be in cartesian coordinates unless self.units=='radec' 
            and self.origin=='sky', then positions are assumed to be pmra,pmdec,vlos (mas/yr, mas/yr, km/s)
        m: float int
            stellar mass
        id: int 
            star id
        do_key_params: bool
            call key_params() after adding stars (default: False)
        do_order: bool
            order stars by radius when calling key_params() (default: False)

        Returns
        ----------

        None

        History
        ----------

        2018 - Written - Webb (UofT)

        """

        self.x = np.append(self.x, np.asarray(x))
        self.y = np.append(self.y, np.asarray(y))
        self.z = np.append(self.z, np.asarray(z))
        self.vx = np.append(self.vx, np.asarray(vx))
        self.vy = np.append(self.vy, np.asarray(vy))
        self.vz = np.append(self.vz, np.asarray(vz))

        if m is None:
            m = np.ones(len(self.x),float)
 
        self.m = np.append(self.m, np.asarray(m))

        if id is None:
            id = np.linspace(0, len(self.x) - 1, len(self.x), dtype=int)

        self.id = np.append(self.id, np.asarray(id))

        # Check lengths

        length_error=False
        nmax = np.amax(
            [
                len(self.id),
                len(self.m),
                len(self.x),
                len(self.y),
                len(self.z),
                len(self.vx),
                len(self.vy),
                len(self.vz),
            ]
        )
        nmin = np.amin(
            [
                len(self.id),
                len(self.m),
                len(self.x),
                len(self.y),
                len(self.z),
                len(self.vx),
                len(self.vy),
                len(self.vz),
            ]
        )
        if nmax != nmin:
            if len(self.id) == 1:
                self.id = np.linspace(0, nmax - 1, nmax, dtype=int)
            elif len(self.id)<nmax:
                length_error=True

            if len(self.m) == 1:
                self.m = np.ones(nmax) * self.m[0]
            elif len(self.m <nmax):
                length_error=True

            if len(self.x) == 1:
                self.x = np.ones(nmax) * self.x[0]
            elif len(self.x <nmax):
                length_error=True

            if len(self.y) == 1:
                self.y = np.ones(nmax) * self.y[0]
            elif len(self.y <nmax):
                length_error=True

            if len(self.z) == 1:
                self.z = np.ones(nmax) * self.z[0]
            elif len(self.z <nmax):
                length_error=True

            if len(self.vx) == 1:
                self.vx = np.ones(nmax) * self.vx[0]
            elif len(self.vx <nmax):
                length_error=True

            if len(self.vy) == 1:
                self.vy = np.ones(nmax) * self.vy[0]
            elif len(self.vy <nmax):
                length_error=True

            if len(self.vz) == 1:
                self.vz = np.ones(nmax) * self.vz[0]
            elif len(self.vz <nmax):
                length_error=True

        if length_error:
            print('ONE OR MORE INPUT ARRAY HAS INCORRECT LENGTH')

        if self.units == "radec" and self.origin == "sky":
            self.ra = copy(self.x)
            self.dec = copy(self.y)
            self.dist = copy(self.z)
            self.pmra = copy(self.vx)
            self.pmdec = copy(self.vy)
            self.vlos = copy(self.vz)

        self.kw = np.append(self.kw, np.zeros(len(self.id)))

        self.rv3d()

        if do_key_params:
            self.key_params(do_order=do_order)

        self.ntot = nmax

    def add_orbit(
        self,
        xgc,
        ygc,
        zgc,
        vxgc,
        vygc,
        vzgc,
        ounits=None,
        initialize=False,
        ro=8.0,
        vo=220.0,
    ):
        """ add orbit properties to StarCluster

        Parameters
        ----------
        xgc,ygc,zgc: float
            cluster's galactocentric position
        vxgc,vygc,vzgc: float
            cluster's galactocentric velocity
        ounits: str
            units of position and velocity. Options include 'pckms',
            'kpckms','radec','nbody',and 'galpy'. Values will be converted 
            to match self.units
        initialize: bool
            Initialize a galpy orbit for self.orbit (default: False)
        ro: float
            galpy position scaling parameter (default: 8.)
        vo: float
            galpy velocity scaling parameter (default: 220.)

        Returns
        ----------

        None

        History:
        ----------

        2018 - Written - Webb (UofT)

        """
        if ounits != None and ounits != self.units:
            # First convert to kpckms
            if ounits != "kpckms":
                if ounits == "nbody":
                    xgc *= self.rbar * 1000.0
                    ygc *= self.rbar * 1000.0
                    zgc *= self.rbar * 1000.0
                    vxgc *= self.vstar
                    vygc *= self.vstar
                    vzgc *= self.vstar
                elif ounits == "galpy":
                    xgc *= ro
                    ygc *= ro
                    zgc *= ro
                    vxgc *= vo
                    vygc *= vo
                    vzgc *= vo
                elif ounits == "pckms":
                    xgc /= 1000.0
                    ygc /= 1000.0
                    zgc /= 1000.0

                ounits = "kpckms"

            if self.units == "pckms":
                xgc *= 1000.0
                ygc *= 1000.0
                zgc *= 1000.0
            elif self.units == "nbody":
                xgc *= 1000.0 / self.rbar
                ygc *= 1000.0 / self.rbar
                zgc *= 1000.0 / self.rbar
                vxgc /= self.vstar
                vygc /= self.vstar
                vzgc /= self.vstar
            elif self.units == "galpy":
                xgc /= ro
                ygc /= ro
                zgc /= ro
                vxgc /= vo
                vygc /= vo
                vzgc /= vo

        self.xgc = xgc
        self.ygc = ygc
        self.zgc = zgc
        self.rgc = np.sqrt(xgc ** 2.0 + ygc ** 2.0 + zgc ** 2.0)
        self.vxgc = vxgc
        self.vygc = vygc
        self.vzgc = vzgc

        if self.units == "radec":
            self.ra_gc = xgc
            self.dec_gc = ygc
            self.dist_gc = zgc
            self.pmra_gc = vxgc
            self.pmdec_gc = vygc
            self.vlos_gc = vzgc

        if initialize:
            initialize_orbit(self, from_centre=False)

    def add_nbody6(
        self,
        nc=0,
        rc=0.0,
        rbar=1.0,
        rtide=0.0,
        xc=0.0,
        yc=0.0,
        zc=0.0,
        zmbar=1.0,
        vstar=1.0,
        rscale=1.0,
        ns=0.0,
        nb=0.0,
        np=0.0,
    ):
        """ Add additional information to StarCluster

        - parameters are common output variables in NBODY6
        - values are never adjusted during unit or coordinate changes

        Parameters
        ----------
        nc : int
            number of stars in core (default:0)
        rc : int
            core radius (default:0)
        rbar : float
            scaling factor between NBODY units and pc (default:1.)
        rtide :
            rtide set in the simulation (default:0)
        xc,yc,zc : float
            position of cluster centre (default:0)
        zmbar : float
            scaling factor between NBODY units and Msun (default:1.)
        vstar : float
            scaling factor between NBODY units and km/s (default:1.)
        rscale : float
            the scale radius of data (default:1.)
        ns : int
            number of single stars (default:0)
        nb : int
            number of binary stars (default:0)
        np : int
            number of particles (default:0)

        Returns
        ----------
        None

        History:
        ----------
        2018 - Written - Webb (UofT)
        """
        # Number of stars in the core
        self.nc = nc
        # Core radius
        self.rc = rc
        # Distane scaling parameter
        self.rbar = rbar
        # Tidal limit from NBODY6 (not neccesarily a true tidal radius)
        self.rtide = rtide
        # Center of mass of cluster (x,yz)
        self.xc = xc
        self.yc = yc
        self.zc = zc
        # Mass scaling parameter
        self.zmbar = zmbar
        # Velocity scaling parameter
        self.vstar = vstar
        # Scale radius of cluster
        self.rscale = rscale
        # Number of single stars
        self.ns = ns
        # Number of binary stars
        self.nb = nb
        # Number of particles (from NBODY6 when tidal tail is being integrated)
        self.np = np

    def add_sse(self, kw, logl, logr, ep, ospin):
        """Add stellar evolution information to stars
        
        - parameters are common output variables in NBODY6
        - values are never adjusted during unit or coordinate changes

        Parameters
        ----------
        kw : int
            stellar evolution type (based on NBODY6) 
        logl : float
            log of luminosity
        logr : float
            log of stellar radius
        ep : float
            epoch
        ospin : float
            ospin

        Returns
        ----------
        None

        History:
        ----------
        2018 - Written - Webb (UofT)

        """
        self.kw = np.asarray(kw)
        self.logl = np.asarray(logl)
        self.logr = np.asarray(logr)
        self.lum = 10.0 ** self.logl
        self.ltot = np.sum(self.lum)
        self.ep = np.asarray(ep)
        self.ospin = np.asarray(ospin)

    def add_bse(
        self,
        id1,
        id2,
        kw1,
        kw2,
        kcm,
        ecc,
        pb,
        semi,
        m1,
        m2,
        logl1,
        logl2,
        logr1,
        logr2,
        ep1=None,
        ep2=None,
        ospin1=None,
        ospin2=None,
    ):
        """Add binary star evolution information to stars

        - parameters are common output variables in NBODY6
        - values are never adjusted during unit or coordinate changes

        Parameters
        ----------

        id1/id2 : int
            id of star1 and star2
        kw1/kw2 : int
            stellar evolution tags (for using with NBODY6) 
        kcm : int
            stellar evolution tag for binary star
        ecc : float 
            eccentricity of binary orbit
        pb: float
            period of binary orbit
        semi : float 
            semi major axis of binary orbit
        m1/m2 : float
            masses of binary stars
        logl1/logl2 : float
            luminosities of binary stars
        logr1/logr2 : float
            radii of binary stars
        ep1/ep2 : float
            epochs of binary stars
        ospin1/ospin2 : float
            opsin of binary stars

        Returns
        ----------

        None

        History:
        ----------

        2018 - Written - Webb (UofT)
        """
        self.id1 = np.asarray(id1)
        self.id2 = np.asarray(id2)
        self.kw1 = np.asarray(kw1)
        self.kw2 = np.asarray(kw2)
        self.kcm = np.asarray(kcm)
        self.ecc = np.asarray(ecc)
        self.pb = np.asarray(pb)
        self.semi = np.asarray(semi)
        self.m1 = np.asarray(m1)
        self.m2 = np.asarray(m2)
        self.logl1 = np.asarray(logl1)
        self.logl2 = np.asarray(logl2)
        self.logr1 = np.asarray(logr1)
        self.logr2 = np.asarray(logr2)
        if ep1 is not None:
            self.ep1 = np.asarray(ep1)
            self.ep2 = np.asarray(ep2)
            self.ospin1 = np.asarray(ospin1)
            self.ospin2 = np.asarray(ospin2)

        self.eb=0.5*self.m1*self.m2/self.semi

    def add_energies(self, kin, pot, etot=None):
        """ add energy information for stars 

        - total energy and Q for the cluster are also calculated
        - values are never adjusted during unit or coordinate changes

        Parameters
        ----------
        kin : float
            kinetic energy 
        pot : float
            potentail energy
        etot : float
            total energy - calculated as kin+pot if not given

        Returns
        ----------
        None

        History
        ----------

        2018 - Written - Webb (UofT)

        """

        self.kin = np.array(kin)
        self.pot = np.array(pot)

        if etot==None:
            self.etot=self.kin+self.pot 
        else:
            self.etot = np.array(etot)

        self.ektot = np.sum(self.kin)
        self.ptot = np.sum(self.pot) / 2.0

        if self.ptot == 0.0:
            self.qvir = 0.0
        else:
            self.qvir = self.ektot / self.ptot

    def add_actions(self, JR, Jphi, Jz, OR, Ophi, Oz, TR, Tphi, Tz):
        """ Add action values to the cluster instance

        Parameters
        ----------
        JR,Jphi,Jz : float
            orbit actions
        OR,Ophi,Oz : float
            orbit frequencies
        TR,Tphi,Tz : float
            orbit periods

        Returns
        -------
        None

        History
        --------
        2019 - Written - Webb (UofT)
        """
        self.JR, self.Jphi, self.Jz = JR, Jphi, Jz
        self.OR, self.Ophi, self.Oz = OR, Ophi, Oz
        self.TR, self.Tphi, self.Tz = TR, Tphi, Tz

    def rv3d(self):
        """ Calculate 3D and projected positions and velocities

        Parameters
        ----------

        None

        Returns
        ----------

        None

        History
        ----------

       2019 - Written - Webb (UofT)
        """

        self.r = np.sqrt(self.x ** 2.0 + self.y ** 2.0 + self.z ** 2.0)
        self.rpro = np.sqrt(self.x ** 2.0 + self.y ** 2.0)
        self.v = np.sqrt(self.vx ** 2.0 + self.vy ** 2.0 + self.vz ** 2.0)
        self.vpro = np.sqrt(self.vx ** 2.0 + self.vy ** 2.0)

    def key_params(self, do_order=False):
        """Find key parameters of the cluster 

        - total mass, total luminosity, 10% largrange radius (r10), half-mass radius (r50),10 % lagrage radius (with respect to luminosity - rh10), half-light radius (rh50) are all calculated if necessary information is given
        - r10, r50, rh10, and rh50 also calculated in projection

        Parameters
        ----------

        do_order : bool
            Perform the time consuming task of ordering stars based on radius to find r10,r50, etc. (default:False)

        Returns
        ----------

        None

        History
        ----------

        2018 - Written - Webb (UofT)

        """

        self.mtot = np.sum(self.m)
        self.mmean = np.mean(self.m)
        self.rmean = np.mean(self.r)
        self.rmax = np.max(self.r)

        # Radially order the stars to find half-mass radius
        if do_order:
            self.rorder = np.argsort(self.r)
            if self.projected:
                self.rproorder = np.argsort(self.rpro)

        if self.rorder is not None:
            msum = np.cumsum(self.m[self.rorder])
            indx = msum >= 0.5 * self.mtot
            self.rm = self.r[self.rorder[indx][0]]  
            indx = msum >= 0.1 * self.mtot
            self.r10 = self.r[self.rorder[indx][0]]

        if self.rproorder is not None:
            msum = np.cumsum(self.m[self.rproorder])
            indx = msum >= 0.5 * self.mtot
            self.rmpro = self.rpro[self.rproorder[indx][0]]
            indx = msum >= 0.1 * self.mtot
            self.r10pro = self.rpro[self.rproorder[indx][0]]
        else:
            self.rmpro = 0.0
            self.r10pro = 0.0

        if len(self.logl) > 0 and self.rorder is not None:
            lsum = np.cumsum(self.lum[self.rorder])
            indx = lsum >= 0.5 * self.ltot
            self.rh = self.r[self.rorder[indx][0]]
            indx = lsum >= 0.1 * self.ltot
            self.rh10 = self.r[self.rorder[indx][0]]

            if self.rproorder is not None:
                lsum = np.cumsum(self.lum[self.rproorder])
                indx = lsum >= 0.5 * self.ltot
                self.rhpro = self.rpro[self.rproorder[indx][0]]
                indx = lsum >= 0.1 * self.ltot
                self.rh10pro = self.rpro[self.rproorder[indx][0]]
            else:
                self.rhpro = 0.0
                self.rh10pro = 0.0

    # Directly call from operations.py (see operations.py files for documenation):

    def to_pckms(self, do_key_params=False):
        to_pckms(self,do_key_params=do_key_params)

    def to_kpckms(self, do_key_params=False, ro=8.0, vo=220.0):
        to_kpckms(self,do_key_params=do_key_params,ro=ro,vo=vo)

    def to_nbody(self, do_key_params=False, ro=8.0, vo=220.0):
        to_nbody(self, do_key_params=do_key_params, ro=ro, vo=vo)

    def to_radec(self, do_key_params=False, ro=8.0, vo=220.0):
        to_radec(self, do_key_params=do_key_params, ro=ro, vo=vo)

    def from_radec(self, do_order=False, do_key_params=False):
        from_radec(self, do_order=do_order, do_key_params=do_key_params)

    def to_galpy(self, do_key_params=False, ro=8.0, vo=220.0):
        to_galpy(self, do_key_params=do_key_params, ro=ro, vo=vo)

    def to_units(self, units, do_order=False, do_key_params=False, ro=8.0, vo=220.0):
        to_units(self, units, do_order=do_order, do_key_params=do_key_params, ro=ro, vo=vo)

    def to_centre(self, do_order=False, do_key_params=False, centre_method=None):
        to_centre(self, do_order=do_order, do_key_params=do_key_params, centre_method=centre_method)

    def to_cluster(self, do_order=False, do_key_params=False, centre_method=None):
        to_cluster(self, do_order=do_order, do_key_params=do_key_params, centre_method=centre_method)

    def to_galaxy(self, do_order=False, do_key_params=False):
        to_galaxy(self, do_order=do_order, do_key_params=do_key_params)

    def to_sky(self, do_order=False, do_key_params=False):
        to_sky(self, do_order=do_order, do_key_params=do_key_params)

    def from_sky(self, do_order=False, do_key_params=False):
        from_sky(self, do_order=do_order, do_key_params=do_key_params)

    def to_tail(self, plot=False):
        self.x_tail,self.y_tail,self.z_tail,self.vx_tail,self.vy_tail,self.vz_tail=to_tail(self, plot=plot)
        self.r_tail = np.sqrt(self.x_tail ** 2.0 + self.y_tail ** 2.0 + self.z_tail ** 2.0)
        self.v_tail = np.sqrt(self.vx_tail ** 2.0 + self.vy_tail ** 2.0 + self.vz_tail ** 2.0)

    def to_origin(self, origin, do_order=False, do_key_params=False):
        to_origin(self, origin, do_order=do_order, do_key_params=do_key_params)

    def save_cluster(self):
        self.units0,self.origin0=save_cluster(self)

    def return_cluster(self, units0=None, origin0=None, do_order=False, do_key_params=False):
        if units0==None: units0=self.units0
        if origin0==None: origin0=self.origin0
        return_cluster(self, units0, origin0, do_order=do_order, do_key_params=do_key_params)

    def reset_nbody_scale(self, mass=True, radii=True, rvirial=False, projected=None, **kwargs):
        if projected==None:
            projected=self.projected

        self.zmbar,self.rbar,self.vstar,self.tstar=reset_nbody_scale(self, mass=mass, radii=radii, 
            rvirial=rvirial,projected=projected **kwargs)

    def convert_binary_units(self,param,from_units,to_units):
        convert_binary_units(self,param,from_units,to_units)

    def add_rotation(self, qrot):
        self.x,self.y,self.z,self.vx,self.vy,self.vz=add_rotation(self, qrot)

        self.qrot=qrot

    def virialize(self, specific=True, full=True, projected=None):
        if projected==None:
            projected=self.projected

        self.qv=virialize(self, specific=True, full=True, projected=projected)

        self.vx *= self.qv
        self.vy *= self.qv
        self.vz *= self.qv

    # Directly call from functions.py (see functions.py files for documenation):

    def find_centre(
        self,
        xstart=0.0,
        ystart=0.0,
        zstart=0.0,
        vxstart=0.0,
        vystart=0.0,
        vzstart=0.0,
        indx=None,
        nsigma=1.0,
        nsphere=100,
        density=True,
        rmin=0.1,
        nmax=100,
        ro=8.0,
        vo=220.0,
    ):

        self.xc, self.yc, self.zc,self.vxc, self.vyc, self.vzc=find_centre(self,xstart=xstart,
            ystart=ystart,zstart=zstart,vxstart=vxstart,vystart=vystart,vzstart=vzstart,indx=indx,
            nsigma=nsigma,nsphere=nsphere,density=density,
            rmin=rmin,nmax=nmax,ro=ro,vo=vo)

        if self.origin == "galaxy" or self.origin=='sky':
            self.xgc, self.ygc, self.zgc = self.xc, self.yc, self.zc
            self.vxgc, self.vygc, self.vzgc = self.vxc, self.vyc, self.vzc

            self.xc, self.yc, self.zc = 0.0, 0.0, 0.0
            self.vxc, self.vyc, self.vzc = 0.0, 0.0, 0.0      

    def find_centre_of_density(
        self,
        xstart=0.0,
        ystart=0.0,
        zstart=0.0,
        vxstart=0.0,
        vystart=0.0,
        vzstart=0.0,
        indx=None,
        rmin=0.1,
        nmax=100,
        ro=8.0,
        vo=220.0,
    ):
        self.xc, self.yc, self.zc,self.vxc, self.vyc, self.vzc=find_centre_of_density(self,xstart=xstart,
            ystart=ystart,zstart=zstart,vxstart=vxstart,vystart=vystart,vzstart=vzstart,indx=indx,
            rmin=rmin,nmax=nmax,ro=ro,vo=vo)

    def find_centre_of_mass(self):
        self.xc, self.yc, self.zc,self.vxc, self.vyc, self.vzc=find_centre_of_mass(self)

    def relaxation_time(self, rad=None, multimass=True, projected=None,method='spitzer'):

        if projected==None:
            projected=self.projected

        self.trelax=relaxation_time(self, rad=rad, multimass=multimass, projected=projected,method='spitzer')

    def half_mass_relaxation_time(self, multimass=True, projected=None):
        if projected==None:
            projected=self.projected
        self.trh=half_mass_relaxation_time(self, multimass=multimass, projected=projected)

    def core_relaxation_time(self, multimass=True, projected=None):
        if projected==None:
            projected=self.projected
        self.trc=core_relaxation_time(self, multimass=True, projected=projected)

    def energies(self, specific=True, i_d=None, full=True, projected=None, parallel=False):
        if projected==None:
            projected=self.projected
        ek, pot=energies(self, specific=specific, i_d=i_d, full=full, projected=projected, parallel=parallel)
        self.add_energies(ek, pot)

    def closest_star(self, projected=None):
        if projected==None:
            projected=self.projected

        self.dclosest=closest_star(self, projected=projected)

    def rlagrange(self, nlagrange=10, projected=None):
        if projected==None:
            projected=self.projected
        self.rn = rlagrange(self, nlagrange=nlagrange, projected=projected)

    def virial_radius(self,method='inverse_distance', full=True, H=70.0, Om=0.3, overdens=200.0,
        nrad=20, projected=None, plot=False, **kwargs):
        if projected==None:
            projected=self.projected

        self.rv = virial_radius(self,method=method, full=full, H=H, Om=Om, overdens=overdens,
        nrad=nrad, projected=projected, plot=plot, **kwargs)

    def mass_function(
        self,
        mmin=None,
        mmax=None,
        nmass=10,
        rmin=None,
        rmax=None,
        vmin=None,
        vmax=None,
        emin=None,
        emax=None,
        kwmin=0,
        kwmax=1,
        indx=None,
        mcorr=None,
        projected=False,
        plot=False,
        **kwargs
    ):

        self.mmin=mmin
        self.mmax=mmax

        if projected==None:
            projected=self.projected

        m_mean, m_hist, dm, alpha, ealpha, yalpha, eyalpha = mass_function(
            self,
            mmin=mmin,
            mmax=mmax,
            nmass=nmass,
            rmin=rmin,
            rmax=rmax,
            vmin=vmin,
            vmax=vmax,
            emin=emin,
            emax=emax,
            kwmin=kwmin,
            kwmax=kwmax,
            indx=None,
            mcorr=None,
            projected=projected,
            plot=plot,
            title="GLOBAL",
            **kwargs
        )
        self.alpha = alpha
        self.rn = rlagrange(self, nlagrange=10, projected=projected)
        m_mean, m_hist, dm, alpha, ealpha, yalpha, eyalpha = mass_function(
            self,
            mmin=mmin,
            mmax=mmax,
            nmass=nmass,
            rmin=self.rn[4],
            rmax=self.rn[6],
            vmin=vmin,
            vmax=vmax,
            emin=emin,
            emax=emax,
            kwmin=kwmin,
            kwmax=kwmax,
            indx=None,
            mcorr=None,
            projected=projected,
            plot=plot,
            title="AT R50",
            **kwargs
        )
        self.alpha50 = alpha

    def eta_function(
        self,
        mmin=None,
        mmax=None,
        nmass=10,
        rmin=None,
        rmax=None,
        vmin=None,
        vmax=None,
        emin=None,
        emax=None,
        kwmin=0,
        kwmax=1,
        projected=False,
        plot=False,
        **kwargs
    ):

        self.mmin=mmin
        self.mmax=mmax

        m_mean, sigvm, eta, eeta, yeta, eyeta = eta_function(
            self,
            mmin=mmin,
            mmax=mmax,
            nmass=nmass,
            rmin=rmin,
            rmax=rmax,
            vmin=vmin,
            vmax=vmax,
            emin=emin,
            emax=emax,
            kwmin=kwmin,
            kwmax=kwmax,
            projected=projected,
            plot=plot,
            **kwargs
        )
        self.eta = eta

    # Directly call from orbit.py (see orbit,py files for documentation):

    def rtidal(self, pot=MWPotential2014, rtiterate=0, rtconverge=0.9, rgc=None, ro=8.0, vo=220.0, verbose=False):
        self.rt = rtidal(self, pot=pot, rtiterate=rtiterate,rtconverge=rtconverge, rgc=rgc, ro=ro, vo=vo, verbose=verbose)

    def rlimiting(
        self,
        pot=MWPotential2014,
        rgc=None,
        ro=8.0,
        vo=220.0,
        nrad=20,
        projected=False,
        plot=False,
        verbose=False,
        **kwargs
    ):
        self.rl = rlimiting(
            self,
            pot=pot,
            rgc=rgc,
            ro=ro,
            vo=vo,
            nrad=nrad,
            projected=projected,
            plot=plot,
            verbose=verbose,
            **kwargs
        )

    def initialize_orbit(self, from_centre=False, ro=8.0, vo=220.0):
        self.orbit=initialize_orbit(self, from_centre=from_centre, ro=ro, vo=vo)

    def initialize_orbits(cluster, ro=8.0, vo=220.0):
        self.orbits=initialize_orbits(self, ro=ro, vo=vo)

    def integrate_orbit(cluster, pot=MWPotential2014, tfinal=12.0, 
        nt=1000, ro=8.0, vo=220.0, plot=False):

        self.ts,self.orbit=integrate_orbit(cluster,pot=pot,tfinal=tfinal,
            nt=nt,ro=ro,vo=vo,plot=plot)

    def integrate_orbits(cluster, pot=MWPotential2014, tfinal=12.0, 
        nt=1000, ro=8.0, vo=220.0, plot=False):

        self.ts,self.orbits=integrate_orbits(cluster,pot=pot,tfinal=tfinal,
            nt=nt,ro=ro,vo=vo,plot=plot)

    def orbit_interpolate(self,dt,pot=MWPotential2014,from_centre=False,
        do_tails=False,rmin=None,rmax=None,emin=None,emax=None,ro=8.0,vo=220.0):

        self.x,self.y,self.z,self.vx,self.vy,self.vz=orbit_interpolate(self,dt,pot=pot,from_centre=from_centre,
            do_tails=do_tails,rmin=rmin,rmax=rmax,emin=emin,emax=emax,ro=ro,vo=vo)

        tint=dt / bovy_conversion.time_in_Gyr(ro=ro, vo=vo)

        self.add_orbit(self.orbit.x(tint),self.orbit.y(tint),self.orbit.z(tint),self.orbit.vx(tint),self.orbit.vy(tint),self.orbit.vz(tint),ounits='kpckms')

        self.tphys+=dt

    def orbital_path(cluster,dt=0.1,nt=100,pot=MWPotential2014,from_centre=False,
        skypath=False,initialize=False,ro=8.0,vo=220.0,plot=False):

        if initialize:
            self.tpath,self.xpath,self.ypath,self.zpath,
            self.vxpath,self.vypath,self.vzpath,self.orbit=orbital_path(cluster,dt=dt,nt=nt,pot=pot,from_centre=from_centre,
                skypath=skypath,initialize=initialize,ro=ro,vo=vo,plot=plot)
        else:
            self.tpath,self.xpath,self.ypath,self.zpath,
            self.vxpath,self.vypath,self.vzpath=orbital_path(cluster,dt=dt,nt=nt,pot=pot,from_centre=from_centre,
                skypath=skypath,initialize=initialize,ro=ro,vo=vo,plot=plot)

    def orbital_path_match(self,dt=0.1,nt=100,pot=MWPotential2014,from_centre=False,
        to_path=False,do_full=False,ro=8.0,vo=220.0,plot=False,):

        self.tstar,self.dprog,self.dpath=orbital_path_match(self,dt=dt,nt=nt,pot=pot,
        from_centre=from_centre,to_path=to_path,do_full=do_full,ro=ro,vo=vo,plot=plot,)


    def tail_path(cluster,dt=0.1,nt=100,pot=MWPotential2014,from_centre=False,
        ro=8.0,vo=220.0,plot=False):

        if initialize:
            self.tpath,self.xpath,self.ypath,self.zpath,
            self.vxpath,self.vypath,self.vzpath,self.orbit=orbital_path(cluster,dt=dt,nt=nt,pot=pot,from_centre=from_centre,
                skypath=skypath,initialize=initialize,ro=ro,vo=vo,plot=plot)
        else:
            self.tpath,self.xpath,self.ypath,self.zpath,
            self.vxpath,self.vypath,self.vzpath=orbital_path(cluster,dt=dt,nt=nt,pot=pot,from_centre=from_centre,
                skypath=skypath,initialize=initialize,ro=ro,vo=vo,plot=plot)

    def tail_path_match(self,dt=0.1,nt=100,pot=MWPotential2014,from_centre=False,
        to_path=False,do_full=False,ro=8.0,vo=220.0,plot=False,):

        self.tstar,self.dprog,self.dpath=orbital_path_match(self,dt=dt,nt=nt,pot=pot,
        from_centre=from_centre,to_path=to_path,do_full=do_full,ro=ro,vo=vo,plot=plot,)

    def get_cluster_orbit(gcname="mwglobularclusters",ro=8.0, vo=220.0):
        self.orbit=get_cluster_orbit(gcname=gcname,ro=ro, vo=vo)

    def calc_actions(self, pot=MWPotential2014, ro=8.0, vo=220.0, **kwargs):
        JR, Jphi, Jz, OR, Ophi, Oz, TR, Tphi, Tz = calc_actions(
            self, pot=pot, ro=ro, vo=vo, **kwargs
        )
        self.add_actions(JR, Jphi, Jz, OR, Ophi, Oz, TR, Tphi, Tz)

    def ttensor(self, pot=MWPotential2014, ro=8.0, vo=220.0, eigenval=False):
        self.ttensor=ttensor(self, pot=pot, ro=ro, vo=vo, eigenval=eigenval)

def sub_cluster(
    cluster,
    rmin=None,
    rmax=None,
    mmin=None,
    mmax=None,
    vmin=None,
    vmax=None,
    emin=None,
    emax=None,
    kwmin=0,
    kwmax=15,
    indx=[None],
    projected=False,
    reset_centre=False,
    reset_nbody_scale=False,
    reset_nbody_mass=False,
    reset_nbody_radii=False,
    do_order=False,
    do_key_params=False,
    **kwargs
):
    """Extract a sub population of stars from a StarCluster

    - automatically moves cluster to centre of mass, so all constraints are in clustercentric coordinates and current StarCluster.units

    Parameters
    ----------
   rmin/rmax : float
        minimum and maximum stellar radii
   mmin/mmax : float
        minimum and maximum stellar mass
   vmin/vmax : float
        minimum and maximum stellar velocity
   emin/emax : float
        minimum and maximum stellar energy
   kwmin/kwmax : int
        minimum and maximum stellar type (kw)
   indx : bool
        user defined boolean array from which to extract the subset
   projected : bool 
        use projected values and constraints (default:False)
   reset_centre : bool
        re-calculate cluster centre after extraction (default:False)
   reset_nbody_scale : bool
        reset nbody scaling factors (default:False)
   reset_nbody_mass : bool 
        find new nbody scaling mass (default:False)
   reset_nbody_radii : bool
        find new nbody scaling radius (default:False)
   reset_rvirial : bool
        use virial radius to find nbody scaling radius (default: True)
   reset_projected : bool 
        use projected radii to find nbody scaling radius (default: False)

    Returns
    -------
    StarCluster

    History
    -------
    2018 - Written - Webb (UofT)

    """
    units0, origin0 = cluster.units, cluster.origin
    cluster.to_centre()

    if projected:
        r = cluster.rpro
        v = cluster.vpro
    else:
        r = cluster.r
        v = cluster.v

    if rmin == None:
        rmin = np.amin(r)
    if rmax == None:
        rmax = np.amax(r)
    if vmin == None:
        vmin = np.amin(v)
    if vmax == None:
        vmax = np.amax(v)
    if mmin == None:
        mmin = np.amin(cluster.m)
    if mmax == None:
        mmax = np.amax(cluster.m)

    if emin == None and emax != None:
        eindx = cluster.etot <= emax
    elif emin != None and emax == None:
        eindx = cluster.etot >= emin
    elif emin != None and emax != None:
        eindx = (cluster.etot <= emax) * (cluster.etot >= emin)
    else:
        eindx = cluster.id > -1

    if None in indx:
        indx = cluster.id > -1

    indx *= (
        (r >= rmin)
        * (r <= rmax)
        * (cluster.m >= mmin)
        * (cluster.m <= mmax)
        * (v >= vmin)
        * (v <= vmax)
        * (cluster.kw >= kwmin)
        * (cluster.kw <= kwmax)
        * eindx
    )

    if np.sum(indx) > 0:
        subcluster = StarCluster(
            cluster.tphys,
            units=cluster.units,
            origin=cluster.origin,
            ctype=cluster.ctype,
        )
        subcluster.add_stars(
            cluster.x[indx],
            cluster.y[indx],
            cluster.z[indx],
            cluster.vx[indx],
            cluster.vy[indx],
            cluster.vz[indx],
            cluster.m[indx],
            cluster.id[indx],
        )

        if len(cluster.ra)==len(cluster.x):
            subcluster.ra, subcluster.dec, subcluster.dist = (
                cluster.ra[indx],
                cluster.dec[indx],
                cluster.dist[indx],
            )
            subcluster.pmra, subcluster.pmdec, subcluster.vlos = (
                cluster.pmra[indx],
                cluster.pmdec[indx],
                cluster.vlos[indx],
            )

        subcluster.kw = cluster.kw[indx]

        subcluster.zmbar = cluster.zmbar
        subcluster.rbar = cluster.rbar
        subcluster.vstar = cluster.vstar
        subcluster.tstar = cluster.tstar
        subcluster.projected = cluster.projected
        subcluster.centre_method = cluster.centre_method

        if len(cluster.logl) > 0:
            subcluster.add_sse(
                cluster.kw[indx],
                cluster.logl[indx],
                cluster.logr[indx],
                cluster.ep[indx],
                cluster.ospin[indx],
            )
        if len(cluster.id2) > 0:
            bindx = np.in1d(cluster.id1, cluster.id[indx])
            subcluster.add_bse(
                cluster.id1[bindx],
                cluster.id2[bindx],
                cluster.kw1[bindx],
                cluster.kw2[bindx],
                cluster.kcm[bindx],
                cluster.ecc[bindx],
                cluster.pb[bindx],
                cluster.semi[bindx],
                cluster.m1[bindx],
                cluster.m2[bindx],
                cluster.logl1[bindx],
                cluster.logl2[bindx],
                cluster.logr1[bindx],
                cluster.logr2[bindx],
                cluster.ep1[bindx],
                cluster.ep2[bindx],
                cluster.ospin1[bindx],
                cluster.ospin2[bindx],
            )
        if len(cluster.etot) > 0:
            subcluster.add_energies(
                cluster.kin[indx], cluster.pot[indx],
            )

        if reset_centre:
            subcluster.add_orbit(
                cluster.xgc + cluster.xc,
                cluster.ygc + cluster.yc,
                cluster.zgc + cluster.zc,
                cluster.vxgc + cluster.vxc,
                cluster.vygc + cluster.vyc,
                cluster.vzgc + cluster.vzc,
            )
            subcluster.xc, subcluster.yc, subcluster.zc = 0.0, 0.0, 0.0
            subcluster.vxc, subcluster.vyc, subcluster.vzc = 0.0, 0.0, 0.0
            subcluster.xc, subcluster.yc, subcluster.zc, subcluster.vxc, subcluster.vyc, subcluster.vzc = subcluster.find_centre(
                0.0, 0.0, 0.0
            )

        else:
            subcluster.add_orbit(
                cluster.xgc,
                cluster.ygc,
                cluster.zgc,
                cluster.vxgc,
                cluster.vygc,
                cluster.vzgc,
            )
            subcluster.xc, subcluster.yc, subcluster.zc = (
                cluster.xc,
                cluster.yc,
                cluster.zc,
            )
            subcluster.vxc, subcluster.vyc, subcluster.vzc = (
                cluster.vxc,
                cluster.vyc,
                cluster.vzc,
            )

            subcluster.ra_gc, subcluster.dec_gc, subcluster.dist_gc - cluster.ra_gc, cluster.dec_gc, cluster.dist_gc
            subcluster.pmra_gc, subcluster.pmdec_gc, subcluster.vlos_gc = (
                cluster.pmra_gc,
                cluster.pmdec_gc,
                cluster.vlos_gc,
            )

        if reset_nbody_scale or reset_nbody_mass or reset_nbody_radii:
            subcluster.to_pckms()
            subcluster.key_params(do_order=True)

            subcluster.reset_nbody_scale(mass=reset_nbody_mass,radius=reset_nbody_radii,rvirial=reset_rvirial,projected=reset_projected,**kwargs)

    else:
        subcluster = StarCluster(cluster.tphys)

    cluster.to_origin(origin0)
    cluster.to_units(units0)

    if subcluster.ntot > 0:
        subcluster.to_origin(origin0)
        subcluster.to_units(units0)

    if do_key_params:
        subcluster.key_params(do_order=do_order)

    return subcluster