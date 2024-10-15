#! @KPYTHON3@
#
# kpython safely sets RELDIR, KROOT, LROOT, and PYTHONPATH before invoking
# the actual Python interpreter.

# KPF specific lakeshore controller

#
# #
# Required libraries.
# #
#

import argparse
import atexit
import configparser
import logging
import os
import pathlib
import signal
import sys
import select
import socket
import time
import threading

import SerialStream
import DFW                  # provided by kroot/util/dfw

#
# #
# Main execution, invoked by a check at the tail end of this file.
# #
#

def main():
    parseCommandLine()  # Need to know where the config file is.
    parseConfigFile()
    checkSanity()
    
    # Set handlers to shut down cleanly in all situations.
    atexit.register(shutdown)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    main.serial = SerialStream.factory(main.ip, port=main.port)
    
    # main.socket = InficonSocket(address=main.ip, port=main.port, delimiter='\r', bytes=True)
    
    # Test InficonSocket
    # main.socket.connect()
    # command = "AYT"
    # main.socket.send(command)
    # command = "\x05"
    # main.socket.send(command)
    # print(main.socket.receive_test())
    
    # Test InficonSocketAsyncIO
    # message = b"PRX"
    # loop = asyncio.get_event_loop()
    # main.socket = loop.create_connection(lambda: InficonSocketAsyncIO(message, loop), main.ip, main.port)
    # loop.run_until_complete(main.socket)
    # loop.run_forever()
    # loop.close()
    
    
    # Test
    main.serial.connect()
    command = b"AYT\r\x05\r"
    main.serial.send(command)
    main.serial.send(command)
    main.serial.send(command)
    main.serial.send(command)
    # rv = ''
    rv = main.serial.receive()
    print(rv)
    
    # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #     s.connect((main.ip, int(main.port)))
    #     command = b"COM,1\r\x05\r"
    #     s.send(command)
    #     rv = s.recv(4096)
        
    # print(rv)
    
    # Start up our KTL backend.
    # main.Service = DFW.Service(main.config.get("main", "service"),
    #                            main.config.get("main", "stdiosvc"),
    #                            setupKeywords)   
    

main.config = configparser.ConfigParser()
main.config_file = None
main.ip = None
main.port = None
main.version = '0.1.1'
main.shutdown = threading.Event()
main.serial = None
main.Service = None

def shutdown(*ignored):
    main.shutdown.set()
    
    try:
        main.serial.disconnect()
    except:
        pass
    
    if main.Service != None:
        main.Service["DISP{}STA".format(main.dispnum)].set("shutting down")
        main.Service.shutdown()
        main.Service = None
        os._exit(1)

#
# #
# All Keyword values, with the exception of those that are handled
# purely by the stdiosvc backend, are instantiated in the following
# function, which gets called when our DFW.Service instance is
# initialized in main().
# #
#

def setupKeywords(service):
    
    return

#
# #
# Helper functions.
# #
#

def parseCommandLine():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", help="Print version number", action='store_true')
    parser.add_argument("-c", "--config", help="Overall configuration file location")
    parser.add_argument("--port", help="Port number of the device")
    parser.add_argument("--ip", help="IP address of the device")
    
    args = sys.argv[1:]
    if len(args) == 0:
        parser.print_help()
        sys.exit(0)
    
    args = parser.parse_args(args)
    
    if args.config is not None:
        main.config_file = validateFile(args.config)
    
    if args.ip is not None:  
        main.ip = args.ip
    
    if args.port is not None:
        try:
            main.port = int(args.port)
        except ValueError:
            print("{} is not a valid port".format(args.port))
            sys.exit(1)
        if main.port <= 0:
            print("{} is not a valid port".format(args.port))
            sys.exit(1)
    
    if args.version:
        print("Version: {}".format(main.version))
        sys.exit(0)
    
def validateFile(filename):
    
    if not pathlib.Path(filename).is_file():
        raise ValueError("File does not exits: '{}'".format(filename))
    
    return pathlib.Path(filename).resolve()
        
def parseConfigFile():
    
    if main.config_file is None:
        return
    
    main.config.read(main.config_file)
    if main.port is None:
        try:
            main.ip = main.config.get("device", "address").split()[0]
            main.port = main.config.get("device", "port")
        except Exception as e:
            main.port = None
            main.ip = None
            print("Address and port may be specified in the config file or as --port option and --ip option on start up: {}".format(e))
            sys.exit(0)
    
    try:
        main.dispnum = int(main.config.get("dispatcher", "dispnum").strip())
    except Exception as e:
        print("Cannot retrieve number for dispatcher instance: {}".format(e))
        sys.exit(0)
        
    try:
        main.name = main.config.get("dispatcher", "name").strip()
    except Exception as e:
        print("Cannot retrieve name for dispatcher instance: {}".format(e))
        sys.exit(0)
    
def checkSanity():
    ''' Raise exceptions if something is wrong with the runtime
        configuration, as specified by the configuration file and
        on the command line.
    '''
    
    if main.config_file is None:
        raise ValueError("No configuration file specified")
    
    sections = ("main", "device", "dispatcher")
    
    for section in sections:
        if main.config.has_section(section):
            pass
        else:
            raise configparser.NoSectionError("[{}]".format(section))
        
    main.config.get("main", "service")
    main.config.get("main", "stdiosvc")
    main.config.get("device", "address")
    port = main.config.get("device", "port")
    
    polltime = main.config.get("device", "poll_time")
    try:
        polltime = int(polltime)
    except ValueError:
        print("{} is not a valid integer for the device poll_time, change in {}".format(polltime, main.config_file))
        sys.exit(0)
    if polltime < 1:
        print("{} is too small a value (<) for the device poll_time, change in {}".format(polltime, main.config_file))
        sys.exit(0)
    
    return    
    
def readPar(command):
    ''' Query the target
    '''
    
    # dispsta_val = main.Service["DISP{}STA".format(main.dispnum)].read()
    
    # if main.serial is None or main.serial.socket is None:
    #     disconnect()
    #     dispsta_val = '4'
        
    # if dispsta_val == '1' or dispsta_val == '4' or dispsta_val is None:
    #     connected = initialConnection()
        
    #     if connected is False:
    #         return
    try:
        main.serial.send(command)
    except SerialStream.CommunicationError as e:
        disconnect()
        return
    except Exception as e:
        ostr = "{}: {}".format(type(e), e)
        main.Service.log(logging.ERROR, ostr)
        return
    
    rv = readResponse()
    
    return rv
    
def readResponse():
    msg = ""
    try:
        msg = main.serial.receive()
    except SerialStream.IncompleteResponse:
        pass
    except SerialStream.NoResponse:
        pass
    except UnicodeDecodeError as e:
        ostr = "{}: {}".format(type(e), e)
        main.Service.log(logging.ERROR, ostr)
        
    return msg.strip()
    
def disconnect():
    # if main.serial:
    #     try:
    #         main.serial.disconnect()
    #     except Exception as e:
    #         ostr = "{}: {}".format(type(e), e)
    #         main.Service.log(logging.ERROR, ostr)
    
    # main.Service["{}_REV".format(main.name)].set("")
    # main.Service["{}_SERIAL".format(main.name)].set("")    
    # main.Service["DISP{}MSG".format(main.dispnum)].set("Disconnected to {} {}".format(main.ip, main.port))
    # main.Service["DISP{}STA".format(main.dispnum)].set('4')
    
    return

def initialConnection():
    # connected = False
    # if main.shutdown.isSet():
    #     return False
    
    return True
    

class InficonSocket:
    
    def __init__(self, address, port, delimiter='\r', bytes=False):
        
        self.address = address
        self.port = int(port)
        self.delimiter = delimiter
        self.socket = None
        self.timeout = 1
        self.descriptors = tuple()
        self.connected = False
        self.raw_bytes = bytes
        self.received = None
        
    def connect(self):
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        
        try:
            self.socket.connect((self.address, self.port))
        except socket.timetout:
            print("connection attempt timed out")
        except socket.error:
            print("connection attempt failed")
        except:
            exception = sys.exc_info()[1]
            print("connection attempt failed: {}".format(exception))
            
        self.descriptors = (self.socket,)
        
        self.socket.setblocking(0)
        
        check = self.descriptors
        _readers, writers, errors = select.select((), check, check, 1)
        
        if self.socket in errors:
            print("new connection indicating an error")
        
        if self.socket in writers:
            pass
        else:
            print("new connection not ready to receive commands")
        
        self.connected = True
    
    def disconnect(self):
        
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            except:
                pass
            
            try:
                self.socket.close()
            except:
                pass
            
        self.connected = False
        self.descriptors = tuple()
        self.socket = None
        
    def reconnect(self):
        
        self.disconnect()
        self.connect()
        
    def send(self, message):
            
        if self.delimiter is not None:
            message = message + self.delimiter
            
        if self.raw_bytes == False:
            try:
                message = str(message)
                message = message.encode()
            except AttributeError:
                pass
        else:
            message = bytes(message, 'utf-8')
            
        check = self.descriptors
        _readers, writers, _errors = select.select((), check, (), self.timeout)
        if self.socket in writers:
            pass
        else:
            print("socket not ready to receive data")
            
        sent = 0
        while sent < len(message):
            try:
                newly_sent = self.socket.send(message[sent:])
            except socket.error:
                newly_sent = 0
                
            if newly_sent == 0:
                print("connection lost")
            else:
                sent += newly_sent
                
        return sent
    
    def receive(self, delimiter=None, timeout=None, strip=False, count=None):
        
        begin = time.time()
        
        if delimiter is None:
            delimiter = self.delimiter
        
        if delimiter is not None and count is not None:
            raise ValueError("cannot specify both a delimiter and a count")
        
        if count is not None:
            count = int(count)
            
        if timeout is None:
            timeout = self.timeout
            
        remaining = timeout
        check = self.descriptors
        descriptor = check[0]
        
        while True:
            if self.received is not None:
                if delimiter is not None and delimiter in self.received:
                    chunks = self.received.split(delimiter, 1)
                    message = chunks[0] + delimiter
                    self.received = chunks[1]
                    if len(self.received) == 0:
                        self.received = None
                    break
                elif delimiter is None:
                    if count is not None:
                        if len(self.received) >= count:
                            message = self.received[:count]
                            self.received = self.received[count:]
                            break
                    else:
                        message = self.received
                        self.received = None
                        break
        
            elapsed = time.time() - begin
        
            if elapsed > timeout:
                if count is not None:
                    error = "timeout expired before count reached"
                elif delimiter is None:
                    error = "timeout expired"
                else:
                    error = "timeout expired before delimiter received"
                
                if self.received is None or len(self.received) == 0:
                    print(error)
                else:
                    error += ": " + repr(self.received)
                    print(error)
            else:
                remaining = timeout - elapsed
            
            readers, writers, errors = select.select(check, (), check, remaining)
            if descriptor in errors:
                print("select() indicates an error")
            
            if descriptor in readers:
                received = self.receive_loop()
                
                if self.received is None:
                    self.received = received
                else:
                    self.received += received
                
        if strip == True:
            message = message.strip()
        
        return message
    
    def receive_loop(self):
        
        received = None
        
        while True:
            try:
                chunk = self.socket.recv(4096)
            except socket.error:
                break
            else:
                if self.raw_bytes == False:
                    try:
                        chunk = chunk.decode('utf-8')
                    except AttributeError:
                        pass
                    except UnicodeDecodeError:
                        chunk = chunk.decode('utf-8', 'replace')
            
            if len(chunk) == 0 or chunk == '':
                break
            
            if received is None:
                received = chunk
            else:
                received += chunk
            
        return received
    
    def receive_test(self):
        
        # received = None
        
        # while True:
        #     # try:
        #     #     chunk = self.socket.recv(4096)
        #     # except socket.error:
        #     #     break
            
        #     chunk = self.socket.recv(4096)
            
        #     if len(chunk) == 0 or chunk == '':
        #         break
            
        #     if received is None:
        #             received = chunk
        #     else:
        #         received += chunk
        
        message = None
        
        while True:
            try:
                message = self.socket.recv(4096)
            except OSError:
                break
            
            if len(message) == 0:
                break
        
        return message
        
import asyncio
class InficonSocketAsyncIO(asyncio.Protocol):
    def __init__(self, message, loop):
        self.message = message + b'\r'
        self.loop = loop
        
    def connection_made(self, transport):
        self.transport = transport
        self.transport.write(self.message)
        
        # enquiry = b'\x05\r'
        # self.transport.write(enquiry)
        
    def data_received(self, data: bytes) -> None:
        # print(data.decode('utf-8'))
        print(data)
        self.transport.close()
        
    def connection_lost(self, exc: Exception | None) -> None:
        self.loop.stop()
    
    

    
if __name__ == "__main__":
    main()