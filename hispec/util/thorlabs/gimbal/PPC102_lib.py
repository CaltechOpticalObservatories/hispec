##### IMPORTANT NOTE:: #####
# The PPC102 can(EXTREAMELY RARELY) fall into an "unhappy state" where the user
# is unable to command or query the stage in any way. This state is not reflected
# with software or hardware indications. The issue is that an interupt can get
# out of sync with the internal firmware loop, and you are unable to hop back
# into the loop. SOLUTION:: Power Cycle
#                   -Elijah A-B(Dev of this Library)

import time
import socket
from enum import IntEnum, IntFlag
import logging
import struct
import contextlib
import io

# Should Modify:
# Provide a build mode which does not print
# Can use buildFLG to supress prints and take it in as arg
# Can keep printDev() for printing if really needed

# -- "destination" byte formatting --
# The destination byte in a given packet is based on which hardware element 
#      is being commanded and the length of the message. 
# Hardware element codes:
# - 0x01 (00000001) = host computer [us]
# - 0x11 (00010001) = motherboard [for controller-general commands]
# - 0x21 (00100001) = motor channel 1 [for commands to channel 1]
# - 0x22 (00100010) = motor channel 2
# 
# When a message is going to be >6 bytes long, the MSB must be set. The manual 
#    suggests doing that with a bitwise OR against 0x80 (shown in manual as 'd|')
# - 0x80 (10000000) = used to bit flip the MSB, signaling a longer-than-6-byte message
# 
# Example:
# In the set_position() function, we're can command channel one, so we use 0x21. 
#   Since the command carries data (>6 bytes), we need to OR with 0x80.
#  ==>> 0x21          |       0x80      =       0xA1
#            (00100001) | (10000000) = (10100001)

class PPC102_Coms(object):
    '''Class for controlling the Throlabs PPC102
    ***Device not setting Keys/Intr bits correctly so some items are omitted
        from this code to avoid confusion
        - The output of the device depends solely on the 'enable' bit
    '''

    def __init__(self, IP: str, port: int, timeout: float= 2.0, 
                                                            log: bool = True):
        '''
            Create socket connection instance variable
            Parameters: Ini file and logger bool 
            old default ini params
                (host: str = '192.168.29.100', port: int = 10013, 
                                                        timeout: float = 2.0)
        '''
        # Logger setup
        if log:
            logname = __name__.rsplit(".", 1)[-1]
            self.logger = logging.getLogger(logname)
            self.logger.setLevel(logging.DEBUG)
            log_handler = logging.FileHandler(logname + ".log")
            formatter = logging.Formatter(
                "%(asctime)s--%(name)s--%(levelname)s--%(module)s--"
                "%(funcName)s--%(message)s")
            log_handler.setFormatter(formatter)
            self.logger.addHandler(log_handler)

            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter("%(asctime)s--%(message)s")
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            self.logger.info("Logger initialized for PPC102_Coms")
        else:
            self.logger = None

        # get coms
        self.IP = IP
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.buffsize = 1024
        # Other Instance Variables
        self.sock = None
        self.DELAY = .1  # Number of seconds to wait after writing a message

    ########### Socket Communitcations ###########
    def open(self):
        '''
            Opens connection to device
            -Also queries the device to obtain basic information
            -This serves to confirm communication
            -*Closes Device and reopens if already opens
            RETURNS: True/False based on Successful connection
        '''
        # if instranticated then close and open a new connection
        if self.sock:
            self.close()
        # Try for error handling
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.IP, self.port))
            if self.logger is not None:
                self.logger.info(f"Connected to {self.IP}:{self.port}")
                self.logger.info("Preliminary read_buff to clear buffer: " \
                                    "Sometimes inicializes with 0x00 in buffer")
            else:
                print(f"Connected to {self.IP}:{self.port}")
                print("Preliminary read_buff to clear buffer: " \
                                    "Sometimes inicializes with 0x00 in buffer")
            # silent this single read buff execution!!!
            original_logger_level = None
            if self.logger:
                original_logger_level = self.logger.level
                self.logger.setLevel(100)  # Temporarily silence logger 
                                                        #(higher than CRITICAL)

            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    try:
                        _ = self.read_buff()
                    except Exception:
                        pass
            except Exception:
                pass  # Silently ignore
            finally:
                if self.logger and original_logger_level is not None:
                    self.logger.setLevel(original_logger_level)
            
            return True # Successful Connection to Device
        except socket.error as e:
            if self.logger is not None:
                self.logger.error(f"Socket connection failed: {e}")
            else:
                print(f"Socket connection failed: {e}")
            self.sock = None
            return False #Unsuccessful Connection

    def close(self):
        '''
            Closes the device connection
        '''
        #Socket close in try statements for error handling
        if self.sock:
            try:
                self.sock.close()
                if self.logger is not None:
                    self.logger.info("Socket closed.")
                else:
                    print("Socket closed")
            except socket.error as e:
                if self.logger is not None:
                    self.logger.error(f"Error closing socket: {e}")
                else:
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
        except socket.error as e:
            if self.logger is not None:
                self.logger.error(f"Error sending data: {e}")
            else:
                print(f"Error sending data: {e}")
            #self.close()
        
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
            #print(hex_array)
            return hex_array
        except socket.timeout:
            if self.logger is not None:
                self.logger.error("Read timed out.")
            else:
                print("Read Timed Out")
            return []
        except socket.error as e:
            if self.logger is not None:
                self.logger.error(f"Error receiving data: {e}")
            else:
                print(f"Error receiving data: {e}")
            #self.close()
            return []
    
    def _interpret_bit_flags(self, byte_data):
        """
            Helper function to interpret bits
                All bit interpretation comes from pg.204 of APT Coms Doc
        """
        if len(byte_data) != 4:
            raise ValueError("Expected exactly 4 bytes")

        # Convert from little endian bytes to a 32-bit unsigned integer
        status = int.from_bytes(byte_data, byteorder='little', signed=False)

        # Define bit meanings
        bit_flags = {
            0:  "Piezo actuator connected",
            10: "Position control mode (closed loop)",
            29: "Active (unit is active)",
            31: "Channel enabled",
        }

        # Extract and report set bits
        results = {}
        for bit, description in bit_flags.items():
            results[description] = bool(status & (1 << bit))

        return results


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
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def set_enable(self, channel: int = 0, enable: int = 1):
        '''
            Sets enable on PPC102 Controller
            channel param:(int) 1 or 2
                          NOTE: Default channel is set to 0, This will change both 
                          channels to the desired enable state provided by the user
            enable param:(int) Enable=1 or Disable=2
            Returns: True/False based on successful com send
            **MGMSG_MOD_SET_CHANENABLESTATE**(10 02 Chan_Ident Enable_State d s)
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #check for valid params
            if enable not in (1, 2):
                raise ValueError("Enable state must be 1 (Enable) or 2 (Disable)")
            
            if channel == 0:
                command = bytes([0x10, 0x02, 0x01, enable, 0x21, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                command = bytes([0x10, 0x02, 0x01, enable, 0x22, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                return True
            if channel not in (1, 2):
                raise ValueError("Channel must be 0, 1 or 2")

            chan = 0x20 + channel  # Channel identifier: 0x21 or 0x22
            set_val = enable       # Already an int: 1 or 2

            command = bytes([0x10, 0x02, 0x01, set_val, chan, 0x01])
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
        
    def get_enable(self, channel: int = 0):
        '''
            Gets enable on PPC102 Controller
            channel param:(int) 1 or 2
                          NOTE: channel=0 will query both channels, returning a 
                                list (channel 1 result, channel 2 result)
            Returns: enable state for that channel as int
            **MGMSG_MOD_REQ_CHANENABLESTATE**(11 02 Chan_Ident 0 d s)
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check channels
            if channel == 0:
                # Construct command: [0x11, 0x02, 0x01, 0x00, chan, 0x01]
                command = bytes([0x11, 0x02, 0x01, 0x00, 0x21, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                ch1 = self.read_buff()
                ch1_state = ch1[3]
                if len(ch1) != 6:
                    raise BufferError("Invalid number of bytes received")
                
                command = bytes([0x11, 0x02, 0x01, 0x00, 0x22, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                ch2 = self.read_buff()
                ch2_state = ch2[3]
                if len(ch2) != 6:
                    raise BufferError("Invalid number of bytes received")

                # retrun loop state
                return int(ch1_state[2:],16), int(ch2_state[2:],16)
            if channel not in (1, 2):
                raise ValueError("Channel must be 0, 1 or 2")

            # Send Req Enable Command
            chan = 0x20 + channel
            command = bytes([0x11, 0x02, 0x01, 0x00, chan, 0x01])

            # REQ
            self.write(command)
            time.sleep(self.DELAY)  # Wait Delay time for write

            # returns self.logger.errored state of Channel and Enable
            enable_status = self.read_buff()
            if len(enable_status) == 0:
                raise BufferError("Buffer empty when expecting response")

            enable_state = enable_status[3]  # This should be a single byte
            return int(enable_state[2:],16)  # Already an int if read_buff 
                                                        #returns a byte array
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return -1

    def _set_digital_outputs(self,channel:int = 1, bit=0000):
        '''
            Sets Digital Output on PPC102 Controller
            (Trigger Fucntionality must be disabled by calling set_trigger first)
            channel param:(int) 1 or 2
            bit param:1111 for all on and 0000 for all off
                            (Only capable of all or nothing setting)
            Returns: True/False based on successful com send
            **MGMSG_MOD_SET_DIGOUTPUTS**(13 02 Bit 00 d s)**

            NOTE: Only sets all on or all off, must implment more detailed 
            controls if you need it

        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            chan = 0x20 + channel  # '2' + channel, as hex

            # Validate bit
            if bit == 0b1111:
                set_val = 0x0F
            elif bit == 0b0000:
                set_val = 0x00
            else:
                raise ReferenceError('Bit not valid – must be 0b0000 or 0b1111')

            # Construct command
            command = bytes([
                0x13,  # ID
                0x02,  # Param 1
                set_val,  # Bits
                0x00,  # Unused
                chan,  # Destination (e.g., 0x21 for channel 1)
                0x01   # Source
            ])

            # Send MGMSG_MOD_SET_DIGOUTPUTS command
            self.write(command)
            time.sleep(self.DELAY)  # Wait for execution of set
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False

    def _get_digital_outputs(self,channel:int = 1, bit=0000):
        '''
            Gets Digital Output on PPC102 Controller
            channel param:(int) 1 or 2
            Returns: Bit
            **MGMSG_MOD_REQ_DIGOUTPUTS**(14 02 Bits 00 d s)**

            NOTE:: bit not requred but original logic from maunal includes

        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            chan = 0x20 + channel  # '2' + channel, as hex

            # Validate bit (not strictly needed for a "get", 
            #                                  but preserved from original logic)
            if bit == 0b1111:
                set_val = 0x0F
            elif bit == 0b0000:
                set_val = 0x00
            else:
                raise ReferenceError('Bit not valid - must be 0b0000 or 0b1111')

            # Construct command
            command = bytes([
                0x14,  # ID
                0x02,  # Param 1
                set_val,  # Bits
                0x00,  # Unused
                chan,  # Destination
                0x01   # Source
            ])

            # Send MGMSG_MOD_REQ_DIGOUTPUTS command
            self.write(command)
            time.sleep(self.DELAY)  # Wait for response

            # Read response
            digioutputs_status = self.read_buff()
            if len(digioutputs_status) == 0:
                raise BufferError("Buffer empty when expecting response")

            # Parse status byte (typically at index 2 or 3 depending on format)
            digioutputs_state = digioutputs_status[2]
            return int(digioutputs_state[2:],16)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def _hw_disconnect(self):
        '''
            Sent by hardware unit or host to disconnect from Ethernet or USB bus
            Returns: True/False based on successful com send
            **MGMSG_HW_DISCONNECT**(02 00 00 00 d s)**

            NOTE:: Do not disconnect, this would require a power cycle as there
            is noreconnect set of bytes to send based on the thorlabs comms 
            documentation

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
            if self.logger is not None:
                self.logger.info("Disconnected from Hardware")
            else:
                print("Disconnected from Hardware")
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
    
    def _hw_response(self):
        '''
            Sent by the controllers to notify Thorlabs Server of some event that 
                requires user intervention, usually some fault or error condition 
                that needs to be handled before normal operation can resume. The 
                message transmits the fault code as a numerical value--see the 
                Return Codes listed in the Thorlabs Server helpfile for details 
                on the specific return codes. 
            Returns: return code
            **MGMSG_HW_RESPONSE**(80 00 00 00 d s)**

            NOTE:: According to thor labs technical team, this function and 
            hw_richresponse are messages that we recieve from the hardware. 
            Rare occation.

        '''
        raise NotImplementedError("MGMSG_HW_RESPONSE: Has not been fully implemented")
         # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send Req response Command
            command = bytes([0x80, 0x00, 0x00, 0x00, 0x11, 0x01])
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed 
            res = self.read_buff()
            if(len(res) == 0):
                raise BufferError("Buffer empty when expecting response")
            return res  # TODO: Optional – parse return code if needed
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def _hw_richresponse(self): #TODO:: Finish
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

            NOTE:: HW_Response and HW_RichResponse basically do the same thing, 
            these are usually sent by the controller indicating some sort of fault 
            that needs to be addressed by the user before continuing. The only 
            difference being that RichResponse gives you a text string to help 
            debug the fault. I've never seen these be returned before so they 
            don't come up very often.
        '''
        raise NotImplementedError("MGMSG_HW_RICHRESPONSE: Has not been fully implemented")
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send Req rich response Command
            command = bytes([
                0x81, 0x00, 0x44, 0x00, 0x11, 0x01, 0x00, 0x00, 0x00, 0x00
                ])
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed
            res = self.read_buff()
            if(len(res) == 0):
                raise BufferError("Buffer empty when expecting response")
            return res  # TODO: Optional – parse message content
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def _hw_start_update_msgs(self):
        '''
            Sent to start automatic status updates from the embedded 
                controller. Status update messages contain information about the 
                position and status of the controller (for example limit switch 
                status, motion indication, etc). The messages will be sent by 
                the controller every 100 msec until it receives a STOP STATUS 
                UPDATE MESSAGES command. In applications where spontaneous 
                messages (i.e., messages which are not received as a response to
                a specific command) must be avoided the same information can 
                also be obtained by using the relevant GET_STATUTSUPDATES function.   
            Returns: True/False on successful com send
            **MGMSG_HW_START_UPDATEMSGS**(11 00 unused unused d s)**

            NOTE: This function starts the polling loop inside the hardware that is
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Send start update response Command
            command = bytes([0x11, 0x00, 0x00, 0x00, 0x11, 0x01])
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state 
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
    
    def _hw_stop_update_msgs(self):
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
            command = bytes([0x12, 0x00, 0x00, 0x00, 0x11, 0x01])
            #REQ
            self.write(command) 
            time.sleep(self.DELAY)  # Wait Delay time for write
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False

    def _get_info(self):#TODO:: Parse this message
        '''
            Sent to request hardware information from the controller.
            Returns: True/False on successful com send
            **MGMSG_HW_REQ_INFO**(05 00 00 00 d s)**

            NOTE:: Response Data Packet Not parsed yet
            - This function is used to get the hardware information from the 
                controller, such as firmware version, serial number, etc

        '''
        raise NotImplementedError(" MGMSG_HW_REQ_INFO Correctly send and " \
                                                    "recieved but not parsed ")
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
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def get_rack_bay_used(self, bay:int = 0):
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
            if 0 <= bay < 10:
                set_val = bay  # already an integer, 0–9
            else:
                raise ReferenceError('Bay Out of Range')

            # Send Req digioutput Command
            command = bytes([0x60, 0x00, set_val, 0x00, 0x11, 0x01])

            # REQ
            self.write(command)
            time.sleep(self.DELAY)  # Wait Delay time for write

            # Read and process response
            bay_res = self.read_buff()
            if len(bay_res) == 0:
                raise BufferError("Buffer empty when expecting response")

            bay_state = bay_res[3]  # Already an int if read_buff returns bytes/bytearray
            return int(bay_state[2:],16) == 1
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def set_loop(self, channel: int = 0, loop:int = 1):
        '''
            Sets the loop to open or closed on each channel
                -Must change for each channel to have a completely closed loop
                -each channel must be enabled
            channel:(int) 1 or 2 
                    NOTE: Default channel is set to 0, This will change both 
                    loops to the desired state the user is attempting to set it to
            loop: Loop state int:   1 Open Loop (no feedback)  
                                    2 Closed Loop (feedback employed)  
                                    3 Open Loop Smooth 
                                    4 Closed Loop Smooth 
            **MGMSG_PZ_GET_POSCONTROLMODE**(41 06 Chan_Iden
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_POSCONTROLMODE**(40 06 Chan_Ident Mode d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check valid loop state
            if loop in (1,2,3,4):
                set_val = loop
            else:
                raise ReferenceError('Loop mode out of range (must be 1,2,3 or 4)')
            
            # Validate channel
            if channel == 0:
                #Check for enable, instruct to set enable if needed
                if (self.get_enable(channel = 1) == DATA_CODES.CHAN_DISABLED or 
                            self.get_enable(channel = 2) == DATA_CODES.CHAN_DISABLED):
                    raise PermissionError(
                        'Channel must be enabled.\n'
                        '  Solution: call set_enable(channel= , enable=1)')
                command = bytes([0x40, 0x06, 0x01, set_val, 0x21, 0x01])
                self.write(command)
                command = bytes([0x40, 0x06, 0x01, set_val, 0x22, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                return True
            elif channel not in (1, 2):
                raise ValueError("Channel must be 0, 1 or 2")
            
            chan = 0x20 + channel  # '2' + channel, as hex

            # Construct command: [0x40, 0x06, 0x01, set_val, chan, 0x01]
            #Check for enable, instruct to set enable if needed
            if (self.get_enable(channel) == DATA_CODES.CHAN_DISABLED):
                raise PermissionError(
                    'Channel must be enabled.\n'
                    '  Solution: call set_enable(channel= , enable=1)')
            command = bytes([0x40, 0x06, 0x01, set_val, chan, 0x01])
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
    
    def get_loop(self, channel: int = 0):
        '''
            Gathers the current state of a channels loop
            channel:(int) 1 or 2
                    NOTE: channel=0 will query both channels, returning a 
                          list (channel 1 result, channel 2 result)
            Returns: Loop state int 1 Open Loop (no feedback)  
                                    2 Closed Loop (feedback employed)  
                                    3 Open Loop Smooth 
                                    4 Closed Loop Smooth 
            **MGMSG_PZ_GET_POSCONTROLMODE**(41 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel == 0:
                # Construct command: [0x41, 0x06, 0x01, 0x00, chan, 0x01]
                command = bytes([0x41, 0x06, 0x01, 0x00, 0x21, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                ch1 = self.read_buff()
                ch1_state = ch1[3]
                if len(ch1) != 6:
                    raise BufferError("Invalid number of bytes received")
                
                command = bytes([0x41, 0x06, 0x01, 0x00, 0x22, 0x01])
                self.write(command)
                time.sleep(self.DELAY)
                ch2 = self.read_buff()
                ch2_state = ch2[3]
                if len(ch2) != 6:
                    raise BufferError("Invalid number of bytes received")

                # retrun loop state
                return int(ch1_state[2:],16), int(ch2_state[2:],16)
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            chan = 0x20 + channel  # '2' + channel, as hex

            # Construct command: [0x41, 0x06, 0x01, 0x00, chan, 0x01]
            command = bytes([0x41, 0x06, 0x01, 0x00, chan, 0x01])
            self.write(command)
            time.sleep(self.DELAY)

            loop_status = self.read_buff()
            loop_state = loop_status[3]
            if len(loop_status) != 6:
                raise BufferError("Invalid number of bytes received")

            # retrun loop state
            return int(loop_state[2:],16)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
        
    def are_loops_closed(self, channel: int = 0):
        '''
            Uses the get_loop function that returns an int to return a 
            boolean for the state of the loops
            channel: 0=both loops
                     1=channel 1 loop
                     2=channel 2 loop
            returns: Bool True(int returned = 2) False(int returned = 1)
            NOTE: ONLY returns true when both channels are in a closed-loop
                  state. will return true/false if querying for individual 
                  channel
        '''
        loop_state = self.get_loop(channel)
        if isinstance(loop_state, tuple):
            return loop_state[0] == 2 and loop_state[1] == 2
        return loop_state == 2
    
    def set_output_volts(self, channel: int = 1, volts:int = 0):
        '''
            Sets voltage going to specified channel
                -Must be in open loop
                -each channel must be enabled
            channel:(int) 1 or 2
            volts:(int) -32768 --> 32767
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_OUTPUTVOLTS**(43 06 04 00 d s Chan_Ident(x2bytes) 
                                                                Volts(x2bytes))**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel) | 0x80  # '2' + channel, as hex

            # Check if channel is enabled
            if self.get_enable(channel) == DATA_CODES.CHAN_DISABLED:
                raise PermissionError('Channel Must Be enabled\n' +
                    '  solution: call set_enable(channel= , enable=1)')     

            # Check if loop is open
            if self.get_loop(channel) == DATA_CODES.CLOSED_LOOP:
                raise PermissionError("Loops Must be OPEN")

            # Check voltage range
            if -32768 < volts < 32767:
                volts_bytes = volts.to_bytes(2, byteorder='little', signed=True)
            else:
                if self.logger is not None:
                    self.logger.error('Voltage out of Range')
                else:
                    print('Voltage out of Range')
                return False

            # Channel identifier (usually 0x01 0x00)
            chan_ident = bytes([0x01, 0x00])

            # Build command
            command = bytes([0x43, 0x06, 0x04, 0x00,destination,
                0x01,]) + chan_ident + volts_bytes

            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
    
    def get_output_volts(self, channel: int = 1):
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
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)

            # Only proceed if open loop and enabled
            if (self.get_loop(channel) == DATA_CODES.OPEN_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):

                # Construct command
                command = bytes([0x44, 0x06, 0x01, 0x00,destination,0x01 ])
                self.write(command)
            else:
                raise PermissionError("Loops Must be OPEN and channel must be " \
                                                                    "enabled")

            time.sleep(self.DELAY)

            # Read response
            volts = self.read_buff()
            if len(volts) != 10:
                raise BufferError("Buffer did not return expected response " \
                                                            "length (10 bytes)")

            # Voltage is in bytes 8 and 9 (little endian hex strings like '0xA3', '0x00')
            low_byte = int(volts[8], 16)   # LSB
            high_byte = int(volts[9], 16)  # MSB

            # Convert to signed 16-bit int
            voltage_raw = (high_byte << 8) | low_byte
            if voltage_raw >= 0x8000:
                voltage_raw -= 0x10000
            return voltage_raw
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def set_position(self, channel: int = 1, pos:float = 0.00):
        '''
            Sets the position of the stage channel
                -only settable while in closed loop
            pos: (float-10.0 mRad -> +10.0 mRad
            Returns: True or False based on successful com send
            NOTE:Sending Controller 0 --> 32767 based on the angular range 
                    user provides
            **MGMSG_PZ_SET_OUTPUTPOS**(46 06 04 00 d s Chan_Ident(x2bytes) 
                                                                Pos(x2bytes))**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel) | 0x80 

            #Check for enable, set enable if needed
            if self.get_enable(channel) == DATA_CODES.CHAN_DISABLED:
                raise PermissionError('Channel Must Be enabled\n' +
                    '  solution: call set_enable(channel= , enable=1)')     

            #check for loop state
            if self.get_loop(channel) == DATA_CODES.OPEN_LOOP:
                raise PermissionError("Loops Must be Closed")

            #Check for valid inputs
            converted_pos = int(round((pos + 10)/20*32767))
            #Check Loop State
            if 0 <= converted_pos <= 32767:
                pos_bytes = converted_pos.to_bytes(2, byteorder='little', signed=False)
            else:
                if self.logger is not None:
                    self.logger.error('Position out of Range')
                else:
                    print('Position out of Range')
                return False

            #Write command
            command = bytes([0x46, 0x06, 0x04, 0x00,destination, 0x01,
                0x01, 0x00,pos_bytes[0], pos_bytes[1] ])
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
        
    def get_position(self, channel: int = 1):
        '''
            Gets Positional Value of an axis of a stage
                -can only read positions while in closed loop
            channel: (int) 1 0r 2
            Returns: -10.0 mRad -> 10.0 mRad 
            NOTE:Contoller return 0 --> 32768 and converted is converted
                    to the angular range
            **MGMSG_PZ_REQ_OUTPUTPOS**(47 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)

            # Send Req OUTPUTPOS command if in closed loop
            if (self.get_loop(channel) == DATA_CODES.CLOSED_LOOP and
                    self.get_enable(channel) == DATA_CODES.CHAN_ENABLED):
                command = bytes([0x47, 0x06, 0x01, 0x00,destination, 0x01])
                self.write(command) #REQ
            else:
                raise PermissionError("Loops Must be Closed and channel must be " \
                                                                    "enabled")

            time.sleep(self.DELAY)  # Wait Delay time for write

            #returns printed state of Channel and Enable
            pos = self.read_buff()
            if(len(pos) == 0):
                raise BufferError("Buffer empty when expecting response")

            #Return Positional Value, 2hex or the positional value in int(bytes 8 and 9)
            # Convert hex string to bytes and parse little-endian unsigned int
            low_byte = int(pos[8], 16)
            high_byte = int(pos[9], 16)
            position = (high_byte << 8) | low_byte

            #Convert for user readability
            if position > 32767:
                position =  32767 - position
            mRad_pos = (position / 32767) * 20 - 10

            return mRad_pos
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def get_max_travel(self, channel: int = 1):
        '''
            In the case of actuators with built in position sensing, the 
                Piezoelectric Control Unit can detect the range of travel of the 
                actuator since this information is programmed in the electronic 
                circuit inside the actuator. This function retrieves the maximum 
                travel for the piezo actuator associated with the channel specified 
                by the Chan Ident parameter, and returns a value (in microns) in the 
                Travel parameter. 
            channel: (int) 1 0r 2
            Returns: travel of a single acuator in microns(Linear Travel) not 
                        Angular travel
                        (ThorLabs Support states: 10nm of linear travel equates
                        to about 20 mrad of angular movement in the mount)
            **MGMSG_PZ_REQ_MAXTRAVEL**(50 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)

            # Send Req
            command = bytes([0x50, 0x06, 0x01, 0x00,destination, 0x01])
            self.write(command) #REQ

            time.sleep(self.DELAY)  # Wait Delay time for write

            #returns printed state of Channel and Enable
            trav = self.read_buff()
            if(len(trav) == 0):
                raise BufferError("Buffer empty when expecting response")

            #Return travitional Value, 2hex or the travitional value in int(bytes 8 and 9)
            byte1 = int(trav[8], 16)
            byte2 = int(trav[9], 16)
            hexVal = byte2 << 8 | byte1
            return hexVal
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def get_status_bits(self, channel: int = 1):
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
            
            NOTE::Bit status comes from pg.204 of thor labs APT Coms documentation

        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)

            # Send
            command = bytes([0x5B, 0x06, 0x01, 0x00,destination, 0x01])
            self.write(command) #REQ

            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            status = self.read_buff()
            if len(status) < 12:
                raise BufferError("Buffer empty when expecting response")

            # Collect status bytes 8 through 11 (LSB to MSB)
            status_bytes = bytes(int(b, 16) for b in status[8:12])
            
            #deliver to interpret bytes function
            results = self._interpret_bit_flags(status_bytes)
            
            if self.logger is not None:
                self.logger.info("Status Flags:", results)
            else:
                print("Status Flags:", results)

            return results
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def get_status_update(self, channel: int = 1):
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
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)

            command = bytes([0x60, 0x06, 0x01, 0x00,destination, 0x01])
            self.write(command) #REQ
            time.sleep(self.DELAY)  # Wait Delay time for write
            #returns printed state of Channel and Enable
            status = self.read_buff()
            if len(status) < 16:
                raise BufferError("Buffer empty when expecting response")

            volt_bytes = bytes(int(b, 16) for b in status[8:10])
            pos_bytes  = bytes(int(b, 16) for b in status[10:12])
            stat_bytes = bytes(int(b, 16) for b in status[12:16])

            voltage = int.from_bytes(volt_bytes, byteorder='little')
            position = int.from_bytes(pos_bytes, byteorder='little')
            #Convert for user readability
            if position > 32767:
                position =  32767 - position
            mRad_pos = (position / 32767) * 20 - 10
            flags = self._interpret_bit_flags(stat_bytes)
            #flags = self.interpret_bit_flags(stat_bytes)

            if self.logger is not None:
                self.logger.info(f"Voltage: {voltage}")
                self.logger.info(f"Position: {mRad_pos}")
            else:
                print(f"Voltage: {voltage}")
                print(f"Position: {mRad_pos}")
                print(f"Status bytes: {flags}")

            return voltage, mRad_pos, flags
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None
    
    def set_max_output_voltage(self, channel: int = 1, limit:int = 150):
        '''
            The piezo actuator connected to the unit has a specific maximum 
                operating voltage range: 75, 100 or 150 V. This function sets the 
                maximum voltage for the piezo actuator associated with the 
                specified channel.  
            channel: (int) 1 or 2
            Returns: True or False on successful com send
            **MGMSG_PZ_SET_OUTPUTMAXVOLTS**(80 06 06 00 d| s Chan_Itent(x2bytes)
                                                                Volts(x2bytes)
                                                                        Flags(x2bytes))**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check for enable, set enable if needed
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            #Convert User friendly volt units to controller expected decavolt units
            limit = limit * 10
            
            destination = (0x20 + channel) | 0x80 
            
            #Check for valid inputs
            if 0 < limit <= 1500:
                hex_val = f'{limit:04X}'
                #Backwards voltage section according to the manual
                #little Edian
                volt_lsb = int(hex_val[2:], 16)
                volt_msb = int(hex_val[:2], 16)
            else:
                raise ValueError('Voltage out of Range')
            
            #Format and write commad
            command = bytes([
                0x80, 0x06, 0x06, 0x00,destination, 0x01, 0x01, 0x00,
                volt_lsb, volt_msb,0x00, 0x00])
            self.write(command)
            time.sleep(self.DELAY)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return False
        
    def get_max_output_voltage(self, channel: int = 1):
        '''
            Gets Max voltage for associated channel 
            channel: (int) 1 or 2
            Returns: Max Volts (0v --> 150v)
            **MGMSG_PZ_GET_OUTPUTMAXVOLTS**(81 06 Chan_Ident 00 d s)**
        '''
        # Check if socket is open
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            # Validate channel
            if channel not in (1, 2):
                raise ValueError("Channel must be 1 or 2")
            
            destination = (0x20 + channel)
            
            #Send command for reqOUTPUTMAXVOLTS
            command = bytes([0x81, 0x06, 0x01, 0x00,destination, 0x01])
            self.write(command)
            time.sleep(self.DELAY)
            msg = self.read_buff()
            if(len(msg) == 0):
                raise BufferError("Buffer empty when expecting response")
            byte1 = int(msg[8], 16)
            byte2 = int(msg[9], 16)
            max_volts = byte2 << 8 | byte1
            max_volts = max_volts/10
            return max_volts
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error: {e}")
            else:
                print(f"Error: {e}")
            return None

    def _set_ppc_PIDCONSTS(self, channel: int = 1, p_const: float = 900.0, 
                           i_const: float = 800.0, d_const: float = 90.0, 
                           dfc_const: float = 1000.0, derivFilter: bool = True):
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

            TODO:: tests
        '''
        raise NotImplementedError("MGMSG_PZ_SET_PPC_PIDCONSTS: Implemented but " \
                                                                    "not tested")
        #check Connection
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        
        try:
            if 0 < channel < 3:
                destination = (0x20 + channel) | 0x80

            if not all(0 <= val <= 10000 for val in (p_const, i_const, 
                                                     d_const, dfc_const)):
                raise ValueError("PID values must be between 0 and 10000")

            chan_ident = (1).to_bytes(2, byteorder='little')

            # Convert PID values to little-endian 2-byte words
            p_bytes = int(p_const).to_bytes(2, byteorder='little')
            i_bytes = int(i_const).to_bytes(2, byteorder='little')
            d_bytes = int(d_const).to_bytes(2, byteorder='little')
            dfc_bytes = int(dfc_const).to_bytes(2, byteorder='little')
            filter_flag = (1 if derivFilter else 2).to_bytes(2, byteorder='little')

            # Header: 90 06 0C 00 d s
            # Assuming destination is generic device 0xD0 and source is 0x01
            header = bytes([0x90, 0x06, 0x0C, 0x00, destination, 0x01])
            data = chan_ident + p_bytes + i_bytes + d_bytes + dfc_bytes + filter_flag

            packet = header + data
            self.write(packet)
            time.sleep(self.DELAY)

            if self.logger is not None:
                self.logger.info(f"PID constants sent: P={p_const}, "\
                    "I={i_const}, D={d_const}, DFC={dfc_const}, "\
                    "Filter={'ON' if derivFilter else 'OFF'}")
            else:
                print(f"PID constants sent: P={p_const}, I={i_const}, "\
                      "D={d_const}, DFC={dfc_bytes}, "\
                      "Filter={'ON' if derivFilter else 'OFF'}")
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in set_pid_consts: {e}")
            else:
                print(f"Error in set_pid_consts: {e}")
            return False
    
    def _get_ppc_PIDCONSTS(self, channel:int = 1):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_PIDCONSTS**(91 06 Chan_Ident 00 d s )**

            NOTE:: Parsing seems to be incorrect

        '''
        raise NotImplementedError("MGMSG_PZ_GET_PPC_PIDCONSTS: " \
                                            "Parseing seems to be Incorrect")
        # check connection
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        
        try:
            if 0 < channel < 3:
                destination = (0x20 + channel)
            else:
                raise ReferenceError("Channel must be 1 or 2.")

            chan_ident = (1).to_bytes(1, byteorder='little')

            # Header for GET command: 91 06 + ChanIdent + 00 + d + s
            header = bytes([0x91, 0x06]) + chan_ident + bytes([0x00, destination, 0x01])
            self.write(header)
            time.sleep(self.DELAY)
            
            response = self.read_buff()
            #Make into bytes for easier parsing
            response_bytes = bytes([int(b, 16) for b in response])

            # Parse the 12-byte payload from byte 6 onwards
            p_const = int.from_bytes(response_bytes[8:10], byteorder='little')
            i_const = int.from_bytes(response_bytes[10:12], byteorder='little')
            d_const = int.from_bytes(response_bytes[12:14], byteorder='little')
            dfc_const = int.from_bytes(response_bytes[14:16], byteorder='little')
            deriv_filter_flag = int.from_bytes(response_bytes[16:18], byteorder='little')
            deriv_filter = True if deriv_filter_flag == 1 else False

            pid_consts = {
                'p_const': p_const,
                'i_const': i_const,
                'd_const': d_const,
                'dfc_const': dfc_const,
                'derivFilter': deriv_filter
            }

            if self.logger is not None:
                self.logger.info(f"Retrieved PID constants: {pid_consts}")
            else:
                print(f"Retrieved PID constants: {pid_consts}")

            return pid_consts

        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in get_pid_consts: {e}")
            else:
                print(f"Error in get_pid_consts: {e}")
            return None
    
    def _set_ppc_NOTCHPARAMS(self, channel: int, filterNO: int,
                          filter_1fc: float, filter_1q: float, notch_filter1_on: bool,
                          filter_2fc: float, filter_2q: float, notch_filter2_on: bool):
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

            TODO:: Requires testing
        '''
        # Check for connection
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check Channel and Filter values
            if channel not in [1, 2]:
                raise ValueError("Channel must be 1 or 2")
            if filterNO not in [1, 2, 3]:
                raise ValueError("Filter number must be 1, 2, or 3")

            #Assign values
            destination = (0x20 + channel) | 0x80
            chan_ident = (1).to_bytes(2, byteorder='little')
            filter_no_bytes = filterNO.to_bytes(2, byteorder='little')

            #Notch filters based on bools
            notch1_on_bytes = (1 if notch_filter1_on else 2).to_bytes(2, 'little')
            notch2_on_bytes = (1 if notch_filter2_on else 2).to_bytes(2, 'little')

            #Creation of data packet
            package = (
                    chan_ident +
                    filter_no_bytes +
                    struct.pack('<f', filter_1fc) +
                    struct.pack('<f', filter_1q) +
                    notch1_on_bytes +
                    struct.pack('<f', filter_2fc) +
                    struct.pack('<f', filter_2q) +
                    notch2_on_bytes
                    )

            #Adding header to data packet
            header = bytes([0x93, 0x06, 0x10, 0x00, destination, 0x01])
            datapacket = header + package

            #Write to controler and log to logger
            self.write(datapacket)
            time.sleep(self.DELAY)

            if self.logger is not None:
                self.logger.info(f"Set NotchParams CH{channel}: F1({filter_1fc}"
                    f"Hz/Q={filter_1q})={'ON' if notch_filter1_on else 'OFF'}, "
                    f"F2({filter_2fc}Hz/Q={filter_2q})={'ON' if notch_filter2_on else 'OFF'}")
            else:
                print(f"Set NotchParams CH{channel}: F1({filter_1fc}"
                    f"Hz/Q={filter_1q})={'ON' if notch_filter1_on else 'OFF'}, "
                    f"F2({filter_2fc}Hz/Q={filter_2q})={'ON' if notch_filter2_on else 'OFF'}")

            return True

        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in set_notch_params: {e}")
            else:
                print(f"Error in set_notch_params: {e}")
            return False
    
    def _get_ppc_NOTCHPARAMS(self, channel: int = 1):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_NOTCHPARAMS**(95 06 Chan_Ident 00 d s )**
        '''
        #Check Connection
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check Channel Validity
            if channel not in [1, 2]:
                raise ValueError("Channel must be 1 or 2")

            #Creaste and write request header
            destination = (0x20 + channel)
            chan_ident = (1).to_bytes(1, byteorder='little')

            header = bytes([0x94, 0x06]) + chan_ident + bytes([0x00, destination, 0x01])
            self.write(header)
            time.sleep(self.DELAY)

            # Expecting 6-byte header + 16-byte data = 22 bytes total
            response = self.read_buff()
            #Make into bytes for easier parsing
            response_bytes = bytes([int(b, 16) for b in response])

            # Parse fields
            filterNO = int.from_bytes(response_bytes[8:10], 'little')
            filter_1fc = struct.unpack('<f', response_bytes[10:14])[0]
            filter_1q = struct.unpack('<f', response_bytes[14:18])[0]
            notch1_on = int.from_bytes(response_bytes[18:20], 'little') == 1
            filter_2fc = struct.unpack('<f', response_bytes[20:24])[0]
            filter_2q = struct.unpack('<f', response_bytes[24:28])[0]
            notch2_on = int.from_bytes(response_bytes[28:30], 'little') == 1

            #Package results
            result = {
                'filterNO': filterNO,
                'filter_1fc': filter_1fc,
                'filter_1q': filter_1q,
                'notch_filter1_on': notch1_on,
                'filter_2fc': filter_2fc,
                'filter_2q': filter_2q,
                'notch_filter2_on': notch2_on,
            }

            #Log or print results
            if self.logger is not None:
                self.logger.info(f"Got NotchParams CH{channel}: {result}")
            else:
                print(f"Got NotchParams CH{channel}: {result}")

            return result

        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in get_notch_params: {e}")
            else:
                print(f"Error in get_notch_params: {e}")
            return None
    
    def _set_ppc_IOSETTINGS(self, channel: int = 1, cntl_src:int = 3, 
            monitor_opsig:int = 2, monitor_opbw:int = 1, feedback_src:int = 1, 
            fp_brightness:int = 2, reserved=0):
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
            **MGMSG_PZ_SET_PPC_IOSETTINGS**(96 06 0E 00 d s (14 byte data packet))**

            TODO:: Requires Testing
        '''
        raise NotImplementedError("MGMSG_PPC_IOSETTINGS: Has been implemented but not tested yet")
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check Channel Validity
            if channel not in [1, 2]:
                raise ValueError("Channel must be 1 or 2")
            destination = (0x20 + channel) | 0x80

            #Create values from inputs
            chan_ident = (1).to_bytes(2, 'little')
            cntl_src_bytes = cntl_src.to_bytes(2, 'little')
            monitor_opsig_bytes = monitor_opsig.to_bytes(2, 'little')
            monitor_opbw_bytes = monitor_opbw.to_bytes(2, 'little')
            feedback_src_bytes = feedback_src.to_bytes(2, 'little')
            fp_brightness_bytes = fp_brightness.to_bytes(2, 'little')
            reserved_bytes = reserved.to_bytes(2, 'little')

            #Make Package
            package = (
                chan_ident +
                cntl_src_bytes +
                monitor_opsig_bytes +
                monitor_opbw_bytes +
                feedback_src_bytes +
                fp_brightness_bytes +
                reserved_bytes
            )

            # Connect Header and write
            header = bytes([0x96, 0x06, 0x0E, 0x00, destination, 0x01])
            datapacket = header + package
            self.write(datapacket)
            if self.logger is not None:
                self.logger.info(
                        f"Set IOSettings CH{channel}: "
                        f"ControlSrc={cntl_src}, MonitorOutSig={monitor_opsig}, MonitorOutBW={monitor_opbw}, "
                        f"FeedbackSrc={feedback_src}, FPBrightness={fp_brightness}, Reserved={reserved}"
                    )
            else:
                print(
                    f"Set IOSettings CH{channel}: "
                    f"ControlSrc={cntl_src}, MonitorOutSig={monitor_opsig}, MonitorOutBW={monitor_opbw}, "
                    f"FeedbackSrc={feedback_src}, FPBrightness={fp_brightness}, Reserved={reserved}"
                )

            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in set_ppc_IOSETTINGS: {e}")
            else:
                print(f"Error in set_ppc_IOSETTINGS: {e}")
            return False
    
    def _get_ppc_IOSETTINGS(self, channel: int = 1):
        '''
            Gets current state values based on description from set
            channel:(int) 1 or 2
            Returns: PID constants in the same format as the set
            **MGMSG_PZ_GET_PPC_IOSETTINGS**(97 06 01 00 d s )**
        '''
        if not self.sock:
            raise RuntimeError("Socket is not connected.")
        try:
            #Check Channel Validity
            if channel not in [1, 2]:
                raise ValueError("Channel must be 1 or 2")
            destination = (0x20 + channel)
            # Connect Header and write
            header = bytes([0x97, 0x06, 0x01, 0x00, destination, 0x01])
            self.write(header)

            #Read and parse
            res = self.read_buff()
            if res is None:
                return None
            def parse_word(lo_index):
                # Assumes little endian: lo byte at lo_index, hi byte at lo_index + 1
                lo = int(res[lo_index], 16)
                hi = int(res[lo_index + 1], 16)
                return hi << 8 | lo

            return {
                        'channel':        parse_word(6),
                        'cntl_src':       parse_word(8),
                        'monitor_opsig':  parse_word(10),
                        'monitor_opbw':   parse_word(12),
                        'feedback_src':   parse_word(14),
                        'fp_brightness':  parse_word(16),
                        'reserved':       parse_word(18),
                    }
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Error in set_ppc_IOSETTINGS: {e}")
            else:
                print(f"Error in set_ppc_IOSETTINGS: {e}")
            return None
    
    def _set_ppc_EEPROMPARAMS(self, channel, msg_id):
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

            TODO:: implement

        '''
        raise NotImplementedError("MGMSG_PZ_SET_PPC_NOTCHPARAMS: Has not been implemented yet")
        return  None
    
    