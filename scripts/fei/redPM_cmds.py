import ThorlabsPM100
import numpy as np

class redPM_cmds:
    """Class for controlling the Thorlabs Red Power Meter (PM100D)
    NOTE: this is just a wrapper around the ThorlabsPM100 python library
    """

    # Conversion from native units to microWatts
    PD_uW_CONVERSION = 1e6

    def __init__(self,devnm="/dev/ttyPM100D",lambda0=2000):
        '''
        NOTE: the default devnm (/dev/ttyPM100D) assumes you've added a udev rule that
                creates this symlink. Otherwise you'll need to provide the /dev/usbtmc* 
                that corresponds to your PM100D.

              The symlink can be created by adding a new file in /etc/udev/rules.d/
                Contents of that file should be:
                SUBSYSTEMS=="usb", ATTRS{idVendor}=="1313", ATTRS{idProduct}=="8078", SYMLINK+="ttyPM100D", GROUP="dialout"
              The first time you add this rule, remember to reload all rules:
                sudo udevadm control --reload-rules
                sudo udevadm trigger
        '''

        # Save instance variables
        self.devnm = devnm
        self.LAMBDA_0 = lambda0
        self.ISOPEN = False

    def readN(self, NRead):
        """Read NRead samples from power meter
    
        NOTE: this returns a vector of reads, NOT the average
        """
        # Preallocate matrix
        reads = np.full(NRead, np.nan)
        
        # Take readings
        for ind in range(NRead):
            reads[ind] = self.PM.read
        
        return reads
        
    def read_pd(self,nb_values=1):
        """Read desired samples AND return average"""
    
        if not self.ISOPEN:
            raise ConnectionError("Device not connected, please use with a context manager.")
        
        # Do reads and return average
        return self.readN(nb_values).mean()
        
    def set_lambda0(self, lambda0=None):
        if lambda0 is not None:
            self.LAMBDA_0 = lambda0
        self.PM.sense.correction.wavelength = self.LAMBDA_0
        
        return self.get_lambda0
        
    def get_lambda0(self):
        return self.PM.sense.correction.wavelength

    def __enter__(self):
        """Enter the context manager"""

        self.__open()

        return self

    def __exit__(self, type, value, tb):
        """Do cleanup"""

        self.__close()
        
    def __open(self):
        """Open connection to the redPM and set central wavelength"""

        self.inst = ThorlabsPM100.USBTMC(device=self.devnm)
        self.PM = ThorlabsPM100.ThorlabsPM100(self.inst)
        self.ISOPEN = True
        
        # Set central wavelength
        self.set_lambda0()

    def __close(self):
        self.ISOPEN = False

#-- Helper function for quickly doing a burst read
def quick_read_pd(nread):
    with redPM_cmds() as pm:
            pmread = pm.readN(nread)
    return pmread