import time
import socket
from enum import IntEnum, IntFlag

# Should Modify:
# Provide a build mode which does not print
# Can use buildFLG to supress prints and take it in as arg
# Can keep printDev() for printing if really needed

class BIT_CODES(IntFlag):
    P_MOT_PMD_MOTIONERROR	 =	0X00004000	# EVENT STATUS BIT 4. Axis exceeds position error limit (1 - limit exceeded, 0 - within limit). FRONT PANEL LED
    P_MOT_PMD_INSTRERROR	 =	0X00008000	# EVENT STATUS BIT 7. Set for variety of ION module instruction errors (1 - instruction error, 0 - no error).
    P_MOT_PMD_INTERLOCK		 =  0X00010000	# EVENT STATUS BIT 8. Interlock link missing in motor connector (1 - missing, 0 - present).
    P_MOT_PMD_OVERTEMP		 =  0X00020000	# EVENT STATUS BIT 9. ION module overtemperature (1 - over temp, 0 - temp OK).
    P_MOT_PMD_BUSVOLTFAULT	 =	0X00040000	# EVENT STATUS BIT 10. ION bus voltage fault (1 - fault, 0 - OK).
    P_MOT_PMD_COMMUTATIONERR =	0X00080000	# EVENT STATUS BIT 11. Axis commutation error (1 - error, 0 - OK).
    P_MOT_PMD_CURRENTFOLDBACK=	0X01000000	# EVENT STATUS BIT 12. Axis phase current limit (1 - current limit, 0 - current below limit).

class DATA_CODES(IntEnum):
    #Channel States
    CLOSED_LOOP = 2
    OPEN_LOOP = 1
    CHAN_ENABLED = 1
    CHAN_DISABLED = 2

    #GENERAL:

    MG17_OK = 0
    MG17_UNKNOWN_ERR = 10000		# unknown error
    MG17_INTERNAL_ERR = 10001		# FFF server internal error
    MG17_FAILED = 10002			# call failed
    MG17_INVALIDPARAM_ERR = 10003		# invalid parameter
    MG17_SETTINGSNOTFOUND = 10004		# requested settings not found
    MG17_DLLNOTINITIALISED = 10005		# APT DLL not intialised.

    #PC SYSTEM:

    MG17_DISKACCESS_ERR = 10050		# disk access error
    MG17_ETHERNET_ERR = 10051		# Windows sockets or ethernet error
    MG17_REGISTRY_ERR = 10052		# registry access error
    MG17_MEMORY_ERR = 10053		# memory allocation error
    MG17_COM_ERR = 10054			# com system error
    MG17_USB_ERR = 10055			# USB comms error
    MG17_NOTTHORLABSDEVICE_ERR = 10056	# Not Thorlabs USB device error.

    #RACK/ USB UNITS:

    MG17_SERIALNUMUNKNOWN_ERR = 10100	# serial number unknown error
    MG17_DUPLICATESERIALNUM_ERR = 10101	# duplicate serial number error
    MG17_DUPLICATEDEVICEIDENT_ERR = 10102	# duplicate device identifier
    MG17_INVALIDMSGSRC_ERR = 10103		# invalid message source
    MG17_UNKNOWNMSGIDENT_ERR = 10104	# unknown message identifier
    MG17_UNKNOWNHWTYPE_ERR = 10105		# unknown hardware type
    MG17_INVALIDSERIALNUM_ERR = 10106	# invalid serial number
    MG17_INVALIDMSGDEST_ERR = 10107	# invalid message destination
    MG17_INVALIDINDEX_ERR = 10108		# invalid index parameter
    MG17_CTRLCOMMSDISABLED_ERR = 10109	# control hardware comms disabled
    MG17_HWRESPONSE_ERR = 10110		# spontaneous hardware response
    MG17_HWTIMEOUT_ERR = 10111		# timeout occured waiting for hardware response
    MG17_INCORRECTVERSION_ERR = 10112	# incorrect version of embedded code
    MG17_HARDLOCKDRIVER_ERR = 10113	# error accessing hardlock drivers
    MG17_HARDLOCKMISSING_ERR = 10114	# missing hardlock error
    MG17_INCOMPATIBLEHARDWARE_ERR = 10115	# incompatible hardware error
    MG17_OLDVERSION_ERR = 10116		# older version of embedded code that can still be used


    #MOTORS:
    MG17_NOSTAGEAXISINFO = 10150		# stage/axis information not found for motor channel
    MG17_CALIBTABLE_ERR = 10151		# calibration table error
    MG17_ENCCALIB_ERR = 10152		# encoder calibration error
    MG17_ENCNOTPRESENT_ERR = 10153		# encoder not present error
    MG17_MOTORNOTHOMED_ERR = 10154		# motor not homed error
    MG17_MOTORDISABLED_ERR = 10155		# motor disabled error
    MG17_PMDMSG_ERR = 10156		# PMD processor message error
    MG17_PMDREADONLY_ERR = 10157		# PMD based controller stage param 'read only' error
            
    #PIEZOS:

    MG17_PIEZOLED_ERR = 10200		# encoder not present error

    #NANOTRAKS:
    MG17_NANOTRAKLED_ERR = 10250		# encoder not present error
    MG17_NANOTRAKCLOSEDLOOP_ERR = 10251	# closed loop error - closed loop selected with no feedback signal
    MG17_NANOTRAKPOWER_ERR = 10252		# power supply error - voltage rails out of limits

class PPC102_Coms(object):
    '''Class for controlling the Throlabs PPC102
    ***Device not setting Keys/Intr bits correctly so some items are omitted
        from this code to avoid confusion
        - The output of the device depends solely on the 'enable' bit
    '''

    def __init__(self, host: str = '192.168.29.100', port: int = 10013, timeout: float = 2.0):
        '''Create socket connection instance variable
        *devnm should be a string like
        '''
        # Socket Connection Variables
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.buffsize = 1024
        # Other Instance Variables
        self.sock = None
        self.DELAY = .25  # Number of seconds to wait after writing a message

    ########### Socket Communitcations ###########
    def open(self):
        '''
            Opens connection to device
            -Also queries the device to obtain basic information
            -This serves to confirm communication
            -*Closes Device and reopens if already open
        '''
        # if instranticated then close and open a new connection
        if self.sock:
            self.close()
        # Try for error handling
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
        except socket.error as e:
            print(f"Socket connection failed: {e}")
            self.sock = None

    def close(self):
        '''
            Closes the device connection
        '''
        #Socket close in try statements for error handling
        if self.sock:
            try:
                self.sock.close()
                print("Socket closed.")
            except socket.error as e:
                print(f"Error closing socket: {e}")
            finally:
                self.sock = None
    
    def write(self, msg: bytes):
        '''
            Sends a message to the device
            msg should be bytes(ex. b'05 00 00 00 50 01')
            *Data requests using 'write' should be followed by a read
            Otherwise unread items in buffer may cause problems
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")

        # Send message using Socket
        try:
            self.sock.sendall(msg)
            time.sleep(.1)
        except socket.error as e:
            print(f"Error sending data: {e}")
            self.close()
        
    #TODO:: Make signal catcher... I.e : SIGTERM SIGFAULT SIGKILL handle with close()

    def read_buff(self):
        '''
            This function will read socket(max: self.bufssize).
            If buffer had values, it will return those values in hex form for the 
            calling fucntion to disect(Also clears buffer)
        '''
        #Read socket
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #return array of hex values for other functions to Disect
            res = self.sock.recv(self.buffsize)
            hex_array = [f'0x{byte:02X}' for byte in res]
            print(hex_array)
            return hex_array
        except socket.timeout:
            print("Read timed out.")
            return b''
        except socket.error as e:
            print(f"Error receiving data: {e}")
            self.close()
            return b''
    
    #TODO: Finish code and bit interpreters
    def interpret_error_code(self, code: int) -> str:
        try:
            return f"{DATA_CODES(code).name} ({code})"
        except ValueError:
            return f"Unknown error code: {code}"
    
    def interpret_bit_flags(status_bytes):
        code = int.from_bytes(status_bytes, byteorder='little')
        flags = [flag for flag in BIT_CODES if flag & code]
        if flags:
            return [f"{flag.name} ({hex(flag.value)})" for flag in flags]
        else:
            return ["No BIT_CODES set"]


    ######## Functions for Complete Stage Control ########

    def identify(self):
        '''
            Makes device flash screen and LED for 3 seconds
            Useful for identifying connected device Visually
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")

        # Send identify command
        try:
            self.write(bytes([0x23, 0x02, 0x01, 0x00, 0x11, 0x01]))
            time.sleep(3)  # Wait until identify is complete
            self.write(bytes([0x23, 0x02, 0x02, 0x00, 0x11, 0x01]))
            time.sleep(3)
        except socket.error as e:
            print(f"Error: {e}")
    
    def set_enable(self, channel=1, enable=1):
        '''
            Sets enable on PPC102 Controller
            channel param:(int) 1 or 2
            enable param:(int) Enable=1 or Disable=2
            Returns: True/False based on successful com send
            **MGMSG_MOD_SET_CHANENABLESTATE**(10 02 Chan_Ident Enable_State d s)
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            if 0 < enable < 3:
                set_val = '0' + str(enable)
            else:
                raise ReferenceError('Enable Out of Range')
            command = bytes.fromhex('10 02 01 '+ set_val +' '+ chan +' 01')
            # Send MGMSG_MOD_SET_CHANENABLESTATE command
            self.write(command)
            time.sleep(self.DELAY)  # Wait for execution of set
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
        
    def get_enable(self, channel=1):
        '''
            Gets enable on PPC102 Controller
            channel param:(int) 1 or 2
            Returns: enable state for that channel as int
            **MGMSG_MOD_REQ_CHANENABLESTATE**(11 02 Chan_Ident 0 d s)
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req Enable Command
            command = bytes.fromhex('11 02 01 00 '+ chan +' 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            enable_status = self.read_buff()
            if(len(enable_status) == 0):
                raise BufferError("Buffer empty when expecting response")
            enable_state = enable_status[3]
            return int(enable_state[2:],16)
        except Exception as e:
            print(f"Error: {e}")

    def set_digital_outputs(self,channel=1, bit=0000):
        '''
            Sets Digital Output on PPC102 Controller
                (Trigger Fucntionality must be disabled by calling set_trigger first)
            channel param:(int) 1 or 2
            bit param:1111 for all on and 0000 for all off(Only capable of all or nothing setting)
            Returns: True/False based on successful com send
            **MGMSG_MOD_SET_DIGOUTPUTS**(13 02 Bit 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            if bit == 1111:
                set_val = '0F'
            elif bit ==0000:
                set_val = '00'
            else:
                raise ReferenceError('Bit not valid')
            command = bytes.fromhex('13 02 '+ set_val +' 00 '+ chan +' 01')
            # Send MGMSG_MOD_SET_DIGOUTPUTS command
            self.write(command)
            time.sleep(self.DELAY)  # Wait for execution of set
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def get_digital_outputs(self,channel=1, bit=0000):
        '''
            Gets Digital Output on PPC102 Controller
            channel param:(int) 1 or 2
            Returns: Bit
            **MGMSG_MOD_REQ_DIGOUTPUTS**(14 02 Bits 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                return ReferenceError('Channel Out of Range')
            if bit == 1111:
                set_val = '0F'
            elif bit ==0000:
                set_val = '00'
            else:
                raise ReferenceError('Enable Out of Range')
            # Send Req digioutput Command
            command = bytes.fromhex('14 02 '+ set_val +' 00 '+ chan +' 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed
            digioutputs_status = self.read_buff()
            if(len(digioutputs_status) == 0):
                raise BufferError("Buffer empty when expecting response")
            digioutputs_state = digioutputs_status[2]
            return int(digioutputs_state[2:],16)
        except Exception as e:
            print(f"Error: {e}")

    def hw_disconnect(self):
        '''
            Sent by hardware unit or host to disconnect from Ethernet or USB bus
            Returns: True/False based on successful com send
            **MGMSG_HW_DISCONNECT**(02 00 00 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send identify command
            self.write(bytes([0x02, 0x00, 0x00, 0x00, 0x11, 0x01]))
            time.sleep(self.DELAY)  # Data Grab
            res = self.read_buff()
            #Save all info needed into self.variables
            print("Disconnected from Hardware")
        except Exception as e:
            print(f"Error: {e}")
    
    def __hw_response(self):
        '''
            Sent by the controllers to notify Thorlabs Server of some event that 
                requires user intervention, usually some fault or error condition that 
                needs to be handled before normal operation can resume. The 
                message transmits the fault code as a numerical value--see the 
                Return Codes listed in the Thorlabs Server helpfile for details on the 
                specific return codes. 
            Returns: return code
            **MGMSG_HW_RESPONSE**(80 00 00 00 d s)**
        '''
         # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send Req response Command
            command = bytes.fromhex('80 00 00 00 11 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed 
            res = self.read_buff()
            if(len(res) == 0):
                raise BufferError("Buffer empty when expecting response")
            return
        except Exception as e:
            print(f"Error: {e}")
    
    def __hw_richresponse(self): #TODO:: Finish
        '''
            Similarly, to HW_RESPONSE, this message is sent by the controllers 
                to notify Thorlabs Server of some event that requires user 
                intervention, usually some fault or error condition that needs to be 
                handled before normal operation can resume. However, unlike 
                HW_RESPONSE, this message also transmits a printable text string. 
                Upon receiving the message, Thorlabs Server displays both the 
                numerical value and the text information, which is useful in finding 
                the cause of the problem.  
            Returns: 
            **MGMSG_HW_RICHRESPONSE**(81 00 44 00 d s MsgIdent(x2bytes) code(x2bytes))**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send Req rich response Command
            command = bytes.fromhex('81 00 44 00 11 01 00 00 00 00')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed
            res = self.read_buff()
            if(len(res) == 0):
                raise BufferError("Buffer empty when expecting response")
            return
        except Exception as e:
            print(f"Error: {e}")
    
    def __hw_start_update_msgs(self):
        '''
            Sent to start automatic status updates from the embedded 
                controller. Status update messages contain information about the 
                position and status of the controller (for example limit switch status, 
                motion indication, etc). The messages will be sent by the controller 
                every 100 msec until it receives a STOP STATUS UPDATE MESSAGES 
                command. In applications where spontaneous messages (i.e., 
                messages which are not received as a response to a specific 
                command) must be avoided the same information can also be 
                obtained by using the relevant GET_STATUTSUPDATES function.   
            Returns: True/False on successful com send
            **MGMSG_HW_START_UPDATEMSGS**(11 00 unused unused d s)**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send start update response Command
            command = bytes.fromhex('11 00 00 00 11 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state 
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def __hw_stop_update_msgs(self):
        '''
            Sent to stop automatic status updates from the controller – usually 
                called by a client application when it is shutting down, to instruct 
                the controller to turn off status updates to prevent USB buffer 
                overflows on the PC. 
            Returns: True/False on successful com send
            **MGMSG_HW_STOP_UPDATEMSGS**(12 00 unused unused d s)**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send stop update response Command
            command = bytes.fromhex('12 00 00 00 11 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def get_info(self):#TODO:: Parse this message
        '''
            Sent to request hardware information from the controller.
            Returns: True/False on successful com send
            **MGMSG_HW_REQ_INFO**(05 00 00 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send identify command
            self.write(bytes([0x05, 0x00, 0x00, 0x00, 0x11, 0x01]))
            time.sleep(self.DELAY)  # Data Grab
            res = self.read_buff()
            if(len(res) != 90):
                raise BufferError("Buffer empty when expecting response")
            #Save all info needed into self.variables
        except Exception as e:
            print(f"Error: {e}")

    def get_rack_bay_used(self, bay=0):
        '''
            Sent to determine whether the specified bay in the controller is occupied. 
            bay param: int
            Returns: True=Occupied//False=Empty
            **MGMSG_RACK_REQ_BAYUSED**(60 00 Bay_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if -1 < bay < 10:
                set_val = '0' + str(bay)
            else:
                return ReferenceError('Bay Out of Range')
            # Send Req digioutput Command
            command = bytes.fromhex('60 00 '+ set_val +' 00 11 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed
            bay_res = self.read_buff()
            if(len(bay_res) == 0):
                raise BufferError("Buffer empty when expecting response")
            bay_state = bay_res[3]
            if int(bay_state[2:],16) == 1:
                return True
            return False
        except Exception as e:
            print(f"Error: {e}")

    def set_loop(self, channel=1, loop=1):
        '''
            Sets the loop to open or closed on each channel
                -Must change for each channel to have a completely closed loop
                -each channel must be enabled
            channel:(int) 1 or 2
            loop: open=1, closed=2 
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_POSCONTROLMODE**(40 06 Chan_Ident Mode d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:

            #Check for enable, set enable if needed
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            if self.get_enable(channel) == DATA_CODES.CHAN_DISABLED:
                raise PermissionError('Channel Must Be enabled\n' +
                    '  solution: call set_enable(channel= , enable=1)')
            
            #Check for valid inputs
            #Change Loop State
            if 0 < loop < 3:
                set_val = '0' + str(loop)
            else:
                raise ReferenceError('Enable Out of Range')
            #Format and write commad
            command = bytes.fromhex('40 06 01 '+ set_val +' '+ chan +'01')
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def get_loop(self, channel=1):
        '''
            Gathers the current state of a channels loop
            channel:(int) 1 or 2
            Returns: Loop state in int
            **MGMSG_PZ_GET_POSCONTROLMODE**(41 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req Enable Command
            command = bytes.fromhex('41 06 01 00 '+ chan +' 01')
            self.write(command) #REQ
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and loop state
            loop_status = self.read_buff()
            if(len(loop_status) != 6):
                raise BufferError("Invalid number of bytes recieved")
            loop_state = loop_status[3]
            return int(loop_state[2:],16)
        except Exception as e:
            print(f"Error: {e}")
    
    def set_output_volts(self, channel, volts):
        '''
            Sets voltage going to specified channel
                -Must be in open loop
                -each channel must be enabled
            channel:(int) 1 or 2
            volts:(int) -32768 --> 32767
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_OUTPUTVOLTS**(43 06 04 00 d s Chan_Ident(x2bytes) Volts(x2bytes))**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check for enable, set enable if needed
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            if self.get_enable(channel) == DATA_CODES.CHAN_DISABLED:
                raise PermissionError('Channel Must Be enabled\n' +
                    '  solution: call set_enable(channel= , enable=1)')     
            #TODO:: check for loop state too
            if self.get_loop(channel) == DATA_CODES.CLOSED_LOOP:
                raise PermissionError("Loops Must be OPEN")
            
            #Check for valid inputs
            #Check Loop State
            if -32768 < volts < 32764:
                hex = f'{volts:04X}'
                valid_hex  = hex[:2] + ' ' + hex[2:]
            else:
                print('Voltage out of Range')
                return False
            #Write command
            command = bytes.fromhex('43 06 04 00 ' + chan + ' 01 01 00 ' + valid_hex)
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def get_output_volts(self, channel):
        '''
            Gathers the current state of a channels voltage
                -must be in open loop
            channel:(int) 1 or 2
            Returns: Voltage state in int (-32768 --> 32767)
            **MGMSG_PZ_GET_OUTPUTVOLTS**(44 6 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req OUTPUTVOLTS command if in closed loop
            if (self.get_loop(channel) == DATA_CODES.OPEN_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):
                command = bytes.fromhex('44 06 01 00 '+ chan +' 01')
                self.write(command) #REQ
            else:
                raise PermissionError("Loops Must be OPEN and channel must be enabled")
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            volts = self.read_buff()
            if(len(volts) != 10):
                raise BufferError("Buffer empty when expecting response")
            #Return voltsitional Value, 2hex or the voltsitional value in int(bytes 8 and 9)
            byte1 = volts[8]
            byte2 = volts[9]
            hexVal = byte2[2:] + byte1[2: ]#byte1[2:] + byte2[2:]
            return int(hexVal,16)
        except Exception as e:
            print(f"Error: {e}")
    
    def set_position(self, channel=1, pos= 50):
        '''
            Sets the position of the stage channel
                -only settable while in closed loop
            pos: (int) 0 --> 32767
            Returns: True or False based on successful com send
            **MGMSG_PZ_SET_OUTPUTPOS**(46 06 04 00 d s Chan_Ident(x2bytes) Pos(x2bytes))**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check for enable, set enable if needed
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            if self.get_enable(channel) == DATA_CODES.CHAN_DISABLED:
                raise PermissionError('Channel Must Be enabled\n' +
                    '  solution: call set_enable(channel= , enable=1)')     
            #TODO:: check for loop state too
            if self.get_loop(channel) == DATA_CODES.OPEN_LOOP:
                raise PermissionError("Loops Must be Closed")
            
            #Check for valid inputs
            #Check Loop State
            if 0 < pos < 32764:
                hex = f'{pos:04X}'
                valid_hex  = hex[:2] + ' ' + hex[2:]
            else:
                print('Position out of Range')
                return False
            #Write command
            command = bytes.fromhex('46 06 04 00 ' + chan + ' 01 01 00 ' + valid_hex)
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
        
    def get_position(self, channel=1):
        '''
            Gets Positional Value of an axis of a stage
                -can only read positions while in closed loop
            channel: (int) 1 0r 2
            Returns: value within its range 0 --> 32768
            **MGMSG_PZ_REQ_OUTPUTPOS**(47 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req OUTPUTPOS command if in closed loop
            if (self.get_loop(channel) == DATA_CODES.CLOSED_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):
                command = bytes.fromhex('47 06 01 00 '+ chan +' 01')
                self.write(command) #REQ
            else:
                raise PermissionError("Loops Must be Closed and chanel must be enabled")
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            pos = self.read_buff()
            if(len(pos) == 0):
                raise BufferError("Buffer empty when expecting response")
            #Return Positional Value, 2hex or the positional value in int(bytes 8 and 9)
            byte1 = pos[8]
            byte2 = pos[9]
            hexVal = byte2[2:] + byte1[2: ]#byte1[2:] + byte2[2:]
            print(int(hexVal,16))
            return int(hexVal,16)
        except Exception as e:
            print(f"Error: {e}")

    def set_zero(self, channel):
        '''
            This function applies a voltage of zero volts to the actuator 
                associated with the channel specified by the lChanID parameter, and 
                then reads the position. This reading is then taken to be the zero 
                reference for all subsequent position readings. This routine is 
                typically called during the initialisation or re-initialisation of the 
                piezo arrangement. 
            channel:(int) 1 or 2
            returns: true or false on succesful coms send
            **MGMSG_PZ_SET_ZERO**(58 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                return ReferenceError('Channel Out of Range')

            # Send Req set zero command
            command = bytes.fromhex('58 06 01 00 '+ chan +' 01')
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def get_max_travel(self, channel):
        '''
            In the case of actuators with built in position sensing, the 
                Piezoelectric Control Unit can detect the range of travel of the 
                actuator since this information is programmed in the electronic 
                circuit inside the actuator. This function retrieves the maximum 
                travel for the piezo actuator associated with the channel specified 
                by the Chan Ident parameter, and returns a value (in microns) in the 
                Travel parameter. 
            channel: (int) 1 0r 2
            Returns: travel 0 --> 65535
            **MGMSG_PZ_REQ_MAXTRAVEL**(50 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req OUTPUTPOS command if in closed loop
            if (self.get_loop(channel) == DATA_CODES.CLOSED_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):
                command = bytes.fromhex('50 06 01 00 '+ chan +' 01')
                self.write(command) #REQ
            else:
                raise PermissionError("Loops Must be Closed and chanel must be enabled")
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            trav = self.read_buff()
            if(len(trav) == 0):
                raise BufferError("Buffer empty when expecting response")
            #Return travitional Value, 2hex or the travitional value in int(bytes 8 and 9)
            byte1 = trav[8]
            byte2 = trav[9]
            hexVal = byte2[2:] + byte1[2: ]#byte1[2:] + byte2[2:]
            return int(hexVal,16)
        except Exception as e:
            print(f"Error: {e}")

    def get_status_bits(self, channel):
        '''
            Returns a number of status flags pertaining to the operation of the 
                piezo controller channel specified in the Chan Ident parameter.  
                These flags are returned in a single 32 bit integer parameter and can 
                provide additional useful status information for client application 
                development. The individual bits (flags) of the 32 bit integer value 
                are described in the following tables.  
            channel: (int) 1 or 2
            Returns: Status Bytes 4 hex values
            **MGMSG_PZ_REQ_PZSTATUSBITS**(5B 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            # Send Req OUTPUTPOS command if in closed loop
            if (self.get_loop(channel) == DATA_CODES.CLOSED_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):
                command = bytes.fromhex('5B 06 01 00 '+ chan +' 01')
                self.write(command) #REQ
            else:
                raise PermissionError("Loops Must be Closed and chanel must be enabled")
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            status = self.read_buff()
            if(len(status) == 0):
                raise BufferError("Buffer empty when expecting response")
            #Return travitional Value, 2hex or the travitional value in int(bytes 8 and 9)
            byte1 = status[8]
            byte2 = status[9]
            byte3 = status[10]
            byte4 = status[11]
            hexVal = byte2[2:] + byte1[2: ]#byte1[2:] + byte2[2:]
            return int(hexVal,16)
        except Exception as e:
            print(f"Error: {e}")
    
    def get_status_update(self, channel):
        '''
            This function is used in applications where spontaneous status 
                messages (i.e. messages sent using the START_STATUSUPDATES 
                command) must be avoided. 
                Status update messages contain information about the position and 
                status of the controller (for example position and O/P voltage). The 
                messages will be sent by the controller each time the function is 
                called. 
            channel: (int) 1 or 2
            Returns: OPVoltage, Position,StatusBits
            **MGMSG_PZ_REQ_PZSTATUSUPDATE**(60 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')

            command = bytes.fromhex('60 06 01 00 '+ chan +' 01')
            self.write(command) #REQ
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            status = self.read_buff()
            if(len(status) == 0):
                raise BufferError("Buffer empty when expecting response")
            #Return travitional Value, 2hex or the travitional value in int(bytes 8 and 9)
            volt1 = status[8]
            volt2 = status[9]
            pos1 = status[10]
            pos2 = status[11]
            byte1 = status[12]
            byte2 = status[13]
            byte3 = status[14]
            byte4 = status[15]
            voltage = int((volt2[2:] + volt1[2: ]), 16)
            position = int((pos2[2:] + pos1[2: ]), 16)
            #hexVal = byte2[2:] + byte1[2: ]#byte1[2:] + byte2[2:]
            print(voltage)
            print(position)
            print(byte1)
            print(byte2)
            print(byte3)
            print(byte4)
            return 
        except Exception as e:
            print(f"Error: {e}")
    
    def set_output_max_voltages(self, channel=1, limit=1500):
        '''
            The piezo actuator connected to the unit has a specific maximum 
                operating voltage range: 75, 100 or 150 V. This function sets the 
                maximum voltage for the piezo actuator associated with the 
                specified channel.  
            channel: (int) 1 or 2
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_OUTPUTMAXVOLTS**(80 06 06 00 d s Chan_Itent(x2bytes)
                                                                Volts(x2bytes)
                                                                        Flags(x2bytes))**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check for enable, set enable if needed
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            
            #Check for valid inputs
            if 0 < limit < 1500:
                hex = f'{limit:04X}'
                #Backwards voltage section according to the manual
                valid_hex  = hex[2:] + ' ' + hex[:2]
            else:
                raise ValueError('Voltage out of Range')
            #Format and write commad
            command = bytes.fromhex('80 06 06 00 ' + chan + ' 01 01 00 ' + valid_hex)
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
        
    def get_max_voltage(self, channel=1):
        '''
            Gets Max voltage for associated channel 
            channel: (int) 1 or 2
            Returns: Max Volts 0--> 1500(0v --> 150v)
            **MGMSG_PZ_GET_OUTPUTMAXVOLTS**(81 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            if 0 < channel < 3:
                chan = '2' + str(channel)
            else:
                raise ReferenceError('Channel Out of Range')
            
            #Send command for reqOUTPUTMAXVOLTS
            command = bytes.fromhex('81 06 01 00 '+chan+' 01')
            self.write(command)
            time.sleep(self.DELAY)
            msg = self.read_buff()
            if(len(msg) == 0):
                raise BufferError("Buffer empty when expecting response")
            byte1 = msg[8]
            byte2 = msg[9]
            max_volts = byte2[2:] + byte1[2:]
            return int(max_volts,16)
        except Exception as e:
            print(f"Error: {e}")

    def __set_ppc_PIDCONSTS(self, channel, p_const, i_const, d_const, dfc_const, derivFilter=True):
        '''
            When operating in Closed Loop mode, the proportional, integral and 
                derivative (PID) constants can be used to fine tune the behaviour of 
                the feedback loop to changes in the output voltage or position. 
                While closed loop operation allows more precise control of the 
                position, feedback loops need to be adjusted to suit the different 
                types of focus mount assemblies that can be connected to the 
                system. Due to the wide range of objectives that can be used with 
                the PFM450 and their different masses, some loop tuning may be 
                necessary to optimize the response of the system and to avoid 
                instability. 
                This message sets values for these PID parameters. The default 
                values have been optimized to work with the actuator shipped with 
                the controller and any changes should be made with caution. 
            channel: (int) 1 or 2
            p_const: float 0-10000
            i_const: float 0-10000
            d_const: float 0-10000
            dfc_const: float 10000
            derivFilter: True=ON False=OFF
            Returns: True or False based on successful com send
            **MGMSG_PZ_SET_PPC_PIDCONSTS**(90 06 0C 00 d s Chan_Ident(x2bytes)
                                            p_const(x2bytes) i_const(x2bytes)
                                            d_const(x2bytes) dfc_const(x2bytes)
                                            derivFilter(x2bytes))**
        '''
        return
    
    def __get_ppc_PIDCONSTS(self, channel):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_PIDCONSTS**(91 06 Chan_Ident 00 d s )**
        '''
        return
    
    def __set_ppc_NOTCHPARAMS(self, channel, filterNO, filter_1fc, filter_1q, notch_filter1_on, filter_2fc, filter_2q, notch_filter2_on):
        '''
            Due to their construction, most actuators are prone to mechanical 
                resonance at well-defined frequencies. The underlying reason is that 
                all spring-mass systems are natural harmonic oscillators. This 
                proneness to resonance can be a problem in closed loop systems 
                because, coupled with the effect of the feedback, it can result in 
                oscillations. With some actuators, the resonance peak is either weak 
                enough or at a high enough frequency for the resonance not to be 
                troublesome. With other actuators the resonance peak is very 
                significant and needs to be eliminated for operation in a stable 
                closed loop system. The notch filter is an adjustable electronic anti
                resonance that can be used to counteract the natural resonance of 
                the mechanical system.  
                As the resonant frequency of actuators varies with load in addition 
                to the minor variations from product to product, the notch filter is 
                tuneable so that its characteristics can be adjusted to match those 
                of the actuator. In addition to its centre frequency, the bandwidth of 
                the notch (or the equivalent quality factor, often referred to as the 
                Q-factor) can also be adjusted. In simple terms, the Q factor is the 
                centre frequency/bandwidth, and defines how wide the notch is, a 
                higher Q factor defining a narrower ("higher quality") notch. 
                Optimizing the Q factor requires some experimentation but in 
                general a value of 5 to 10 is in most cases a good starting point. 
            channel: (int) 1 or 2
            filterNO: int 1,2,3
            filter_1fc: float  20-500
            filter_1q: float 0.2 100
            notch_filter1_on: word ON or OFF
            filter_2fc: float  20-500
            filter_2q: float 0.2 100
            notch_filter2_on: word ON or OFF
            Returns: true or false based on successful com send
            **MGMSG_PZ_SET_PPC_NOTCHPARAMS**(93 06 10 00 d s (16 byte data packet))**
        '''
        return
    
    def __get_ppc_PIDCONSTS(self, channel=1):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_NOTCHPARAMS**(95 06 Chan_Ident 00 d s )**
        '''
        return
    
    def __set_ppc_IOSETTINGS(self, channel, cntl_src, monitor_opsig, monitor_opbw, feedback_src, fp_brightness, reserved):
        '''
            This message is used to set various input and output parameter 
                values associated with the rear panel BNC IO connectors. 
            channel: (int) 1 or 2
            cntl_src: int 1,2,3,4
            monitor_opsig: int 1,2,3
            monitor_opbw: int 1,2
            feedback_src:int 1,2
            fp_brightness:int 1,2,3
            reserved: reserved
            Returns: true or false based on successful com send
            **MGMSG_PZ_SET_PPC_NOTCHPARAMS**(96 06 0E 00 d s (14 byte data packet))**
        '''
        return
    
    def __get_ppc_IOSETTINGS(self, channel=1):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_IOSETTINGS**(97 06 01 00 d s )**
        '''
        return
    
    def __set_ppc_EEPROMPARAMS(self, channel, msg_id):
        '''
            Used to save the parameter settings for the specified message. 
                These settings may have been altered either through the various 
                method calls or through user interaction with the GUI (specifically, 
                by clicking on the ‘Settings’ button found in the lower right hand 
                corner of the user interface).  
            channel: (int) 1 or 2
            msg_id: word
            Returns: true or false based on successful com send
            **MGMSG_PZ_SET_PPC_NOTCHPARAMS**(96 06 0E 00 d s (14 byte data packet))**
        '''
        return
    