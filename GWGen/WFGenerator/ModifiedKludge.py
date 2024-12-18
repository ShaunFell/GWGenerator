from .Kludge import *
from ..DressedFluxes import *
from ..UndressedFluxes import *
from few.waveform import AAKWaveformBase
import warnings
from ..Utils.HelperFunctions import *


class EMRIWithProcaWaveform(ProcaSolution,AAKWaveformBase, Kerr):
    def __init__(self,
                    inspiral_kwargs={},
                    sum_kwargs={},
                    use_gpu=False,
                    num_threads=None,
                ):
        self.inspiralkwargs = inspiral_kwargs.copy()
        self.sumkwargs = sum_kwargs.copy()
        self.use_gpu = use_gpu
        self.num_threads = num_threads

        AAKWaveformBase.__init__(self,
                            PNTraj,
                            AAKSummation,
                            inspiral_kwargs=self.inspiralkwargs,
                            sum_kwargs = self.sumkwargs,
                            use_gpu=self.use_gpu,
                            num_threads=self.num_threads)

    def __call__(self, InitialSMBHMass, SecondaryMass, ProcaMass, InitialBHSpin, p0, e0, x0, T=1, npoints=10, BosonSpin=1, CloudModel="relativistic", units="physical", FluxName="analytic", UltralightBoson=None, **kwargs):
        qs = kwargs.get("qS", 0)
        phis = kwargs.get("phiS", 0)
        qk = kwargs.get("qK", 0)
        phik = kwargs.get("phiK", 0)
        dist = kwargs.get("dist", 1)
        Phi_phi0 = kwargs.get("Phi_phi0", 0)
        Phi_theta0 = kwargs.get("Phi_theta0",0)
        Phi_r0 = kwargs.get("Phi_r0", 0)
        mich = kwargs.get("mich", False)
        dt = kwargs.get("dt", 15)


        #Instantiates the propeties FinalBHMass and FinalBHSpin to EMRIWithProcaWaveform class
        ProcaSolution.__init__(self,InitialSMBHMass, InitialBHSpin, ProcaMass, BosonSpin=BosonSpin, CloudModel=CloudModel, units=units,UltralightBoson=UltralightBoson) #How to use super() with multiple inheritance with different positional arguments for each __init__?

        MassRatio = SecondaryMass/InitialSMBHMass
        Kerr.__init__(self,BHSpin=InitialBHSpin)


        if e0<1e-6:
            warnings.warn("Eccentricity below safe threshold for FEW. Functions behave poorly for e<1e-6")
            e0=1e-6 #Certain functions in FEW are not well-behaved below this value

        OrbitalConstantsChange = self.ChangeInOrbitalConstants(SecondaryMass=SecondaryMass, SMBHMass=InitialSMBHMass)
        asymptoticBosonCloudEFlux = OrbitalConstantsChange["E"] #Dimensionfull Flux. Mass Ratio prefactor comes from derivative of orbital energy wrt spacetime mass and factor of mass of the geodesic. Takes into account effective mass seen by secondary BH during its orbit
        asymptoticBosonCloudLFlux = OrbitalConstantsChange["L"]


        self.inspiralkwargs["DeltaEFlux"] = asymptoticBosonCloudEFlux
        self.inspiralkwargs["DeltaLFlux"] = asymptoticBosonCloudLFlux
        self.inspiralkwargs["FluxName"] = FluxName


        qS,phiS,qK,phiK = self.sanity_check_angles(qs,phis,qk,phik)

        #Sanity check Initial Parameters
        try:
            self.sanity_check_init(InitialSMBHMass, SecondaryMass,InitialBHSpin,p0,e0,x0)
        except ValueError as err:
            errmessage = "Error in initial parameters sanity check. \n\t SMBHMass: {0} \n\t Secondary Mass: {1} \n\t SMBHSpin: {2} \n\t ProcaMass: {3} \n Error Message: {4}".format(InitialSMBHMass,SecondaryMass, InitialBHSpin, ProcaMass, err.args[0])
            raise ValueError(errmessage)

        #get the Trajectory
        t,p,e,Y,pphi,ptheta,pr = self.inspiral_generator(InitialSMBHMass,SecondaryMass,InitialBHSpin,p0,e0,x0,T=T, dt=dt, Phi_phi0=Phi_phi0, Phi_theta0=Phi_theta0, Phi_r0=Phi_r0, **self.inspiralkwargs)
        self.Trajectory = {"t":t, "p":p, "e":e, "Y":Y, "Phi_phi":pphi, "Phi_theta":ptheta, "Phi_r":pr}

        #Sanity check trajectory
        try:
            self.sanity_check_traj(p,e,Y)
        except ValueError as err:
            errmessage = "Error in trajectory sanity check. \n\t SMBHMass: {0} \n\t Secondary Mass: {1} \n\t SMBHSpin: {2} \n\t ProcaMass: {3} \n Error Message: {4}".format(InitialSMBHMass,SecondaryMass, InitialBHSpin, ProcaMass, err.args[0])
            raise ValueError(errmessage)

        self.end_time = t[-1]

        # number of modes to use (from original AAK model)
        self.num_modes_kept = self.nmodes = int(30 * e0)
        if self.num_modes_kept < 4:
            self.num_modes_kept = self.nmodes = 4

        self.waveform = self.create_waveform(t,InitialSMBHMass,InitialBHSpin,p,e,Y,pphi, ptheta, pr, SecondaryMass,qS,phiS, qK, phiK, dist, self.nmodes,mich=mich,dt=dt,T=T)
        return self.waveform
