import DFW
import pysnmp.hlapi
import sys

# -------------------------------------------------------------------------
# Methods for communicating with the 1-Wire Environmental Sensor
# -------------------------------------------------------------------------

class Commands:
    
    def __init__(self, host, read, write):
        
        # Communication variables
        self.snmp_host = host
        self.snmp_read = read
        self.snmp_write = write
        
        # Cache the pysnmp info instead of creating it every call
        self.snmp_builder = None
        self.snmp_engine = pysnmp.hlapi.SnmpEngine()
        
    def getSNMP(self, oid):
        
        host = self.snmp_host
        community = self.snmp_read
        
        engine = self.snmp_engine
        community = pysnmp.hlapi.CommunityData(community, mpModel=0)
        transport = pysnmp.hlapi.UdpTransportTarget((host, 161), timeout=1, retries=1)
        context = pysnmp.hlapi.ContextData()
        identity = pysnmp.hlapi.ObjectIdentity(oid)
        object = pysnmp.hlapi.ObjectType(identity)
        
        getter = pysnmp.hlapi.getCmd(engine, community, transport, context, object, lookupMib=False)
        
        error_indication = None
        error_status = 0
        
        try:
            result = next(getter)
        except pysnmp.error.PySnmpError:
            result = None
            exception = sys.exc_info()[1]
            error_indication = str(exception)
        else:
            error_indication, error_status, _error_index, var_binds = result
            
            if error_indication is not None:
                result = None
            elif error_status != 0:
                result = None
            else:
                var_bind = var_binds[0]
                # result_oid = var_bind[0]
                result_value = var_bind[1]
                
                result = result_value
                result = str(result)
                
        return result, error_indication, error_status
    
    def setSNMP(self, oid, value):
        
        host = self.snmp_host
        community = self.snmp_write
        
        if isinstance(value, int):
            value = pysnmp.hlapi.Integer(value)
        elif isinstance(value, str):
            value = pysnmp.hlapi.OctetString(value)
        else:
            raise TypeError('SNMP can only handle integer and string values')
        
        engine = self.snmp_engine
        community = pysnmp.hlapi.CommunityData(community, mpModel=0)
        transport = pysnmp.hlapi.Udp6TransportTarget((host, 161), timeout=5.0)
        context = pysnmp.hlapi.ContextData()
        identity = pysnmp.hlapi.ObjectIdentity(oid)
        object = pysnmp.hlapi.ObjectType(identity, value)
        
        setter = pysnmp.hlapi.setCmd(engine, community, transport, context, object, lookupMib=False)
        
        error_indication = None
        error_status = 0
        
        try:
            result = next(setter)
        except pysnmp.error.PySnmpError:
            return False
        else:
            error_indication, error_status, _error_index, _var_binds = result
        
        if error_indication is not None:
            return False
        elif error_status != 0:
            return False

        return True
    
# end of class Commands

# Converting string to int does not work for some reason
class Integer(DFW.Keyword.Integer):

    def __init__(self, name, service, owenv, oid, period=30):

        self.owenv = owenv
        self.snmp = owenv.snmp_object
        self.oid = oid
        
        self.rapid_checks = 0
        self.fast_period = 0.5

        DFW.Keyword.Integer.__init__(self, name, service, period=period)


    def speedUp(self, checks=5):

        self.rapid_checks = checks
        self.period(self.fast_period)


    def slowDown(self):

        # This may throw a KeyError if this keyword isn't set up correctly
        # in self.pdu.periods. That represents a real programming error, we
        # want it to be visible-- and to be fixed. That's why the possible
        # exception isn't caught+logged here.

        self.rapid_checks = 0
        slow_period = self.owenv.periods[self.name]
        self.period(slow_period)


    def read(self):

        result, _error_indication, _error_status = self.snmp.getSNMP(self.oid)

        if result == '':
            result = None

        if self.service is not None:
            status = "OWENV_SNMP"
            try:
                status = self.service[status]
            except KeyError:
                status = None

            if status is not None:
                if result is None:
                    status.failed()
                else:
                    status.restored()
                    
        return result

    def update(self, *args, **kwargs):

        slow_down = False
        if self.rapid_checks == 1:
            slow_down = True
        elif self.rapid_checks > 1:
            self.rapid_checks -= 1

        try:
            DFW.Keyword.String.update(self, *args, **kwargs)
        except:
            if slow_down:
                self.slowDown()
            raise
        else:
            if slow_down:
                self.slowDown()


    def prewrite(self, value):

        status = self.owenv.getOverallStatus()
        if status != 'online':
            message = 'OWENV is offline: ' + str(status)
            DFW.Keyword.raiseError(message, 'ERR_CONTROLLER_GONE')

        return DFW.Keyword.Integer.prewrite(self, value)


    def write(self, value):

        value = int(value)
        self.snmp.setSNMP(self.oid, value)
        self.speedUp()


    def postwrite(self, *args, **kwargs):
        ''' This is a no-op, let update() broadcast the new value.
        '''
        return


# end of class Integer

class Double(DFW.Keyword.Double):

    def __init__(self, name, service, owenv, oid, period=30):

        self.owenv = owenv
        self.snmp = owenv.snmp_object
        self.oid = oid
        
        self.rapid_checks = 0
        self.fast_period = 0.5
        

        DFW.Keyword.Double.__init__(self, name, service, period=period)

    def speedUp(self, checks=5):

        self.rapid_checks = checks
        self.period(self.fast_period)


    def slowDown(self):

        # This may throw a KeyError if this keyword isn't set up correctly
        # in self.pdu.periods. That represents a real programming error, we
        # want it to be visible-- and to be fixed. That's why the possible
        # exception isn't caught+logged here.

        self.rapid_checks = 0
        slow_period = self.owenv.periods[self.name]
        self.period(slow_period)


    def read(self):

        result, _error_indication, _error_status = self.snmp.getSNMP(self.oid)

        if result == '':
            result = None

        if self.service is not None:
            status = "OWENV_SNMP"
            try:
                status = self.service[status]
            except KeyError:
                status = None

            if status is not None:
                if result is None:
                    status.failed()
                else:
                    status.restored()
        
        return result

    def update(self, *args, **kwargs):

        slow_down = False
        if self.rapid_checks == 1:
            slow_down = True
        elif self.rapid_checks > 1:
            self.rapid_checks -= 1

        try:
            DFW.Keyword.String.update(self, *args, **kwargs)
        except:
            if slow_down:
                self.slowDown()
            raise
        else:
            if slow_down:
                self.slowDown()


    def prewrite(self, value):

        status = self.owenv.getOverallStatus()
        print("status" + status)
        if status != 'online':
            message = 'OWENV is offline: ' + str(status)
            DFW.Keyword.raiseError(message, 'ERR_CONTROLLER_GONE')

        return DFW.Keyword.Double.prewrite(self, value)


    def write(self, value):

        value = float(value)
        self.snmp.setSNMP(self.oid, value)
        self.speedUp()


    def postwrite(self, *args, **kwargs):
        ''' This is a no-op, let update() broadcast the new value.
        '''
        return


# end of class Double

class String(DFW.Keyword.String):

    def __init__(self, name, service, owenv, oid, period=30):

        self.owenv = owenv
        self.snmp = owenv.snmp_object
        self.oid = oid

        self.rapid_checks = 0
        self.fast_period = 0.5

        DFW.Keyword.String.__init__(self, name, service, initial='', period=period)


    def speedUp(self, checks=5):

        self.rapid_checks = checks
        self.period(self.fast_period)


    def slowDown(self):

        # This may throw a KeyError if this keyword isn't set up correctly
        # in self.pdu.periods. That represents a real programming error, we
        # want it to be visible-- and to be fixed. That's why the possible
        # exception isn't caught+logged here.

        self.rapid_checks = 0
        slow_period = self.owenv.periods[self.name]
        self.period(slow_period)


    def read(self):

        result, _error_indication, _error_status = self.snmp.getSNMP(self.oid)

        if self.service is not None:
            status = "OWENV_SNMP"
            try:
                status = self.service[status]
            except KeyError:
                status = None

            if status is not None:
                if result is None:
                    status.failed()
                    result = ''
                else:
                    status.restored()

        return result


    def prewrite(self, value):

        status = self.owenv.getOverallStatus()
        if status != 'online':
            message = 'OWENV is offline: ' + str(status)
            DFW.Keyword.raiseError(message, 'ERR_CONTROLLER_GONE')

        return DFW.Keyword.String.prewrite(self, value)


    def write(self, value):

        self.snmp.setSNMP(self.oid, value)
        self.speedUp()


    def postwrite(self, *args, **kwargs):
        ''' This is a no-op, let update() broadcast the new value.
        '''
        return


    def update(self, *args, **kwargs):

        slow_down = False
        if self.rapid_checks == 1:
            slow_down = True
        elif self.rapid_checks > 1:
            self.rapid_checks -= 1

        try:
            DFW.Keyword.String.update(self, *args, **kwargs)
        except:
            if slow_down:
                self.slowDown()
            raise
        else:
            if slow_down:
                self.slowDown()

# end of class String