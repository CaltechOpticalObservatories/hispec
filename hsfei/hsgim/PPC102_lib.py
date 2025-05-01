import serial
import struct
import time
from telnetlib import Telnet
import socket
from enum import IntEnum

# Should Modify:
# Provide a build mode which does not print
# Can use buildFLG to supress prints and take it in as arg
# Can keep printDev() for printing if really needed

class DATA_CODES(IntEnum):
    CLOSED_LOOP = 2
    OPEN_LOOP = 1
    CHAN_ENABLED = 1
    CHAN_DISABLED = 2



class PPC102_Coms(object):
    '''Class for controlling the Throlabs TLS001
    ***Device not setting Keys/Intr bits correctly so some items are omitted
        from this code to avoid confusion
        - The output of the device depends solely on the 'enable' bit
    '''

    DEFAULT_DEVNAME = '/dev/serial/by-id/usb-Thorlabs_APT_Laser_Source_86873430-if00-port0'

    def __init__(self, devnm=DEFAULT_DEVNAME):
        '''Create socket connection instance variable
        *devnm should be a string like
        '''
        # Open Telnet Connection
        self.con = Telnet()
        self.con.host = '192.168.1.100'
        self.con.port = 10012
        self.con.timeout = 1
        self.tmt = 1
        self.VOLMAX = 150
        self.VOLMIN = -25
        # Other Instance Variables
        self.con_type = None
        self.DELAY = .25  # Number of seconds to wait after writing a message

    def open(self):
        '''
            Opens connection to device
            -Also queries the device to obtain basic information
            -This serves to confirm communication
            -*Does not reopen device if already open
        '''
        # if connection is already open, return
        if not self.con_type is None:
            print('Device Already open\n\n')
            return

        self.con.open(self.con.host, self.con.port)
        self.con_type = "telnet"

    def close(self):
        '''
            Closes the device connection
        '''
        self.con.close()
        self.con_type = None
    
    def write(self, hexMSG, byteAppend=None):
        '''
            Sends a message to the device
            hexMSG should be the message as a hex string (ex. '05 00 00 00 50 01')
            Can append a byte (or byte array) to the end of hexMSG with byteAppend
            *Data requests using 'write' should be followed by a read
            Otherwise unread items in buffer may cause problems
        '''
        # Check if port is open
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        msg = bytearray.fromhex(hexMSG)  # convert to bytes

        # Append bytes to end
        if byteAppend != None:
            msg = b''.join((msg, byteAppend))

        # Send message using Telnet
        self.con.write(msg)
        print(msg)

    def read_buff(self):
        '''
            This function will read eagerly 2 times using Telnet so the buffer is clear.
            If buffer had values, it will return those values in hex form for the 
            calling fucntion to disect(Also clears buffer)
        '''
        #Read eagerly until buffer is clear
        res = self.con.read_eager()
        if res != '':
            time.sleep(self.DELAY)
            res = res + self.con.read_eager()
        #return array of hex values for other functions to Disect
        hex_array = [f'0x{byte:02X}' for byte in res]
        return hex_array

    def identify(self):
        '''
            Makes device flash screen and LED for 3 seconds
            Useful for identifying connected device without checking SN
        '''
        # Check if port is open
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return

        # Send identify command
        self.write('23 02 01 00 11 01')
        time.sleep(3)  # Wait until identify is complete
        self.write('23 02 02 00 11 01')
        time.sleep(3)
    
    def get_status(self):
        '''
            Returns the current status of the controller and both channels
        '''
        return
    
    def get_error(self):
        '''
            Returns return code and Description associated with the fault
            While gathering the return code it also clears the error that may be blocking
            the next execution
        '''
        return

    def set_enable(self, channel=1, enable=1):
        '''
            Sets enable on PPC102 Controller
            channel param: 1 or 2
            enable param: Enable=1 or Disable=2
        '''
        # Check if port is open
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return
        if 0 < enable < 3:
            set_val = '0' + str(enable)
        else:
            print('ERROR::: Enable out of Range')
            return

        # Send GMSG_MOD_SET_CHANENABLESTATE command
        self.write('10 02 01 '+ set_val +' '+ chan +'01')
        time.sleep(self.DELAY)  # Wait for execution of set
    
    def get_enable(self, channel=1):
        '''
            Gets Enable status from controller
        '''
         # Check if port is open
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return

        # Send Req Enable Command
        self.write('11 02 01 00 '+ chan +' 01') #REQ
        time.sleep(self.DELAY)  # Wait Delay time for write
        #returns printed state of Channel and Enable
        enable_status = self.read_buff()
        print(enable_status[3])
        enable_state = enable_status[3]
        return int(enable_state[2:],16)
    
    def get_info(self):
        '''
            Makes device flash screen and LED for 3 seconds
            Useful for identifying connected device without checking SN
        '''
        # Check if port is open
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return

        # Send identify command
        self.write('05 00 00 00 11 01')
        time.sleep(self.DELAY)  # Data Grab
        #self.read_all()  
        #Save all info needed into self.variables

    def set_loop(self, channel=1, loop=1):
        '''
            Sets the loop to open or closed on each channel
            -Must change for each channel to have a completely closed loop
            channel: 1 or 2
            loop: open=1, closed=2 
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return

        #Check for enable, set enable if needed
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return
        if self.get_enable(channel) == DATA_CODES.CHAN_ENABLED:
            print('ERROR::: Channel Must Be enabled\n' +
                  '  solution: call set_enable(channel= , enable=1)')
            return      
        
        #Check for valid inputs
           #Change Loop State
        if 0 < loop < 3:
            set_val = '0' + str(loop)
        else:
            print('ERROR::: Enable out of Range')
            return
        self.write('40 06 01 '+ set_val +' '+ chan +'01')
        time.sleep(self.DELAY)
    
    def get_loop(self, channel=1):
        '''
            Gathers the current state of a channels loop
            channel: 1 or 2
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return

        # Send Req Enable Command
        self.write('41 06 01 00 '+ chan +' 01') #REQ
        time.sleep(self.DELAY)  # Wait Delay time for write
        #returns printed state of Channel and loop state
        loop_status = self.read_buff()
        print(loop_status[3])
        loop_state = loop_status[3]
        return int(loop_state[2:],16)
    
    def get_max_voltage(self, channel=1):
        '''
            Returns the current max voltage limit set on the associated channel
            channel: 1 or 2
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return
        
        #Send command for reqOUTPUTMAXVOLTS
        self.write('81 06 01 00 '+chan+' 01')
        time.sleep(self.DELAY)
        msg = self.read_buff()
        byte1 = msg[8]
        byte2 = msg[9]
        max_volts = byte1[2:] + byte2[2:]
        print(int(max_volts,16))
        return int(max_volts,16)
    
    def set_max_voltages(self, channel=1, limit=1250):
        '''
            Sets max voltage limit set on the associated channel
            channel: 1 or 2
            limit: -25(v)-->150(v)
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return

        #Check for enable, set enable if needed
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return  
        
        #Check for valid inputs
           #Change Loop State
        if 0 < limit < 1500:
            hex = f'{limit:04X}'
            print(hex)
            #Backwards voltage section according to the manual
            valid_hex  = hex[2:] + ' ' + hex[:2]
        else:
            print('ERROR::: Voltage out of Range')
            return
        self.write('80 06 06 00 ' + chan + ' 01 01 00 ' + valid_hex)
        time.sleep(self.DELAY)
        return
    
    def get_position(self, channel=1):
        '''
            Gets Positional Value of an axis of a stage
                -can only read positions while in closed loop
            returns value within its range 0 --> 32768
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return

        # Send Req OUTPUTPOS command if in closed loop
        if self.get_loop(channel) == DATA_CODES.CLOSED_LOOP:
            self.write('47 06 01 00 11 01') #REQ
        else:
            print("ERROR::: Loops Must be Closed")
            return
        time.sleep(self.DELAY)  # Wait Delay time for write
        #returns printed state of Channel and Enable
        pos = self.read_buff()
        #Return Positional Value, 2hex or the positional value in int(bytes 8 and 9)
        byte1 = pos[8]
        byte2 = pos[9]
        hexVal = byte1[2:] + byte2[2:]
        print(int(hexVal,16))
        return int(hexVal,16)
    
    def set_position(self, channel=1, pos= 100):
        '''
            Sets the position of the stage channel
                -only settable while in closed loop
                -value must be in range 0 -->
        '''
        #Check for connection
        if self.con_type is None:
            print('ERROR::: Device must be open\n' +
                  '  solution: call open()')
            return

        #Check for enable, set enable if needed
        if 0 < channel < 3:
            chan = '2' + str(channel)
        else:
            print('ERROR::: Channel Out of Range')
            return
        if self.get_enable(channel) == DATA_CODES.CHAN_ENABLED:
            print('ERROR::: Channel Must Be enabled\n' +
                  '  solution: call set_enable(channel= , enable=1)')
            return      
        
        #Check for valid inputs
           #Change Loop State
        if 0 < pos < 32764:
            hex = f'{pos:04X}'
            print(hex)
            valid_hex  = hex[:2] + ' ' + hex[2:]
        else:
            print('ERROR::: Position out of Range')
            return
        self.write('46 06 04 00 ' + chan + ' 01 01 00 ' + valid_hex)
        time.sleep(self.DELAY)
        return
    



'''

'''