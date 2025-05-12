import time
import math
from .units import Units
from .config import DEFAULT_POLI_VALUE, DISABLE_WAITING, DEBUG_MODE, NOT_SETTING_COMMANDS, AUTO_SEND_ENBL
from .utils import outputConsole, getDposEposString, getActualTime

class Axis:
    axis_letter = None  # Stores the axis letter for this specific axis.
    xeryon_object = None  # Stores the "XeryonController" object.
    axis_data = None  # Stores all the data the controller sends.
    settings = None  # Stores all the settings from the settings file
    stage = None  # Specifies the type of stage used in this axis.
    units = Units.mm  # Specifies the units this axis is currently working in.
    update_nb = 0  # This number increments each time an update is recieved from the controller.
    was_valid_DPOS = False  # if True, the STEP command takes DPOS as the refrence. It's called "targeted_position=1/0" in the Microcontroller
    def_poli_value = str(DEFAULT_POLI_VALUE)

    isLogging = False  # Stores if this axis is currently "Logging": it's storing its axis_data.
    logs = {}  # This stores all the data. It's a dictionary of the form:

    previous_epos = [0,0] # Two samples to calculate speed
    previous_time = [0,0]

    # { "EPOS": [...,...,...], "DPOS": [...,...,...], "STAT":[...,...,...],...}

    def findIndex(self, forceWaiting = False, direction=0):
        """
        :return: None
        This function finds the index, after finding the index it goes to the index position.
        It blocks the program until the index is found.
        """
        self.__sendCommand("INDX=" + str(direction))
        self.was_valid_DPOS = False

        if DISABLE_WAITING is False or forceWaiting is True:
            self.__waitForUpdate()  # Waits a couple of updates, so the EncoderValid flag is valid and doesn't lagg behind.
            self.__waitForUpdate()
            outputConsole("Searching index for axis " + str(self) + ".")
            while not self.isEncoderValid():  # While index not found, wait.
                if not self.isSearchingIndex():  # Check if searching for index bit is true.
                    outputConsole("Index is not found, but stopped searching for index.", True)
                    break
                time.sleep(0.2)

        if self.isEncoderValid():
            outputConsole("Index of axis " + str(self) + " found.")

    def move(self, value):
        value = int(value)
        direction = 0
        if value > 0:
            direction = 1
        elif value < 0:
            direction = -1
        self.sendCommand("MOVE=" + str(direction))

    def setDPOS(self, value, differentUnits=None, outputToConsole=True):
        """
        :param value: The new value DPOS has to become.
        :param differentUnits: If the value isn't specified in the current units, specify the correct units.
        :type differentUnits: Units
        :param outputToConsole: Default set to True. If set to False, this function won't output text to the console.
        :return: None
        Note: This function makes use of the sendCommand function, which is blocking the program until the position is reached.
        """
        unit = self.units  # Current units
        if differentUnits is not None:  # If the value given are in different units than the current units:
            unit = differentUnits  # Then specify the unit in differentUnits argument.

        DPOS = int(self.convertUnitsToEncoder(value, unit))  # Convert into encoder units.
        error = False

        self.__sendCommand("DPOS=" + str(DPOS))
        self.was_valid_DPOS = True # And keep it True in order to avoid an accumulating error.

        # Block all futher processes until position is reached.
        if DEBUG_MODE is False and DISABLE_WAITING is False:  # This check isn't nessecary in DEBUG mode or when DISABLE_WAITING is True
            # send_time = getActualTime()
            # distance = abs(int(DPOS) - int(self.getData("EPOS")))  # For calculating timeout time.

            # Wait some updates. This is so the flags (e.g. left end stop) of the previous command aren't received.
            # self.__waitForUpdate()

            # Wait until EPOS is within PTO2 AND positionReached status is received.
            while not (self.__isWithinTol(DPOS) and self.isPositionReached()):

                # Check if stage is at left end or right end. ==> out of range movement.
                if self.isAtLeftEnd() or self.isAtRightEnd():
                    outputConsole("DPOS is out or range. (1) " + getDposEposString(value, self.getEPOS(), unit), True)
                    error = True
                    break

                # # Position reached flag is set, but EPOS not within tolerance of DPOS.
                # if self.isPositionReached() and not self.__isWithinTol(DPOS):
                # # if self.isPositionReached():
                #     # Check if it's a lineair stage and DPOS is beyond it's limits.
                #     if self.stage.isLineair and (
                #             int(self.getSetting("LLIM")) > int(DPOS) or int(self.getSetting("HLIM")) < int(DPOS)):
                #         outputConsole("DPOS is out or range.(2)" + getDposEposString(value, self.getEPOS(), unit), True)
                #         error = True
                #         break

                #     # EPOS is not within tolerance of DPOS, unknown reason.
                #     outputConsole("Position not reached. (3) " + getDposEposString(value, self.getEPOS(), unit), True)
                #     error = True
                #     break
                
                if self.isEncoderError():
                    outputConsole("Position not reached. (4). Encoder gave an error.", True)
                    error = True
                    break
                    
                if self.isErrorLimit():
                    outputConsole("Position not reached. (5) ELIM Triggered.", True)
                    error = True
                    break

                if self.isSafetyTimeoutTriggered():
                    outputConsole("Position not reached. (6) TOU2 (Timeout 2) triggered.", True)
                    error = True
                    break

                if self.isThermalProtection1() or self.isThermalProtection2():
                    outputConsole("Position not reached. (7) amplifier error.", True)
                    error = True
                    break

                # # This movement took too long, timeout time is estimated with speed & distance.
                # if self.__timeOutReached(send_time, distance):
                #     outputConsole(
                #         "Position not reached, timeout reached. (4) " + getDposEposString(value, self.getEPOS(), unit),
                #         True)
                #     error = True
                #     break
                # Keep polling ==> if timeout is not done, the computer will poll too fast. The microcontroller can't follow.
                
                time.sleep(0.01)

        if outputToConsole and error is False and DISABLE_WAITING is False:  # Output new DPOS & EPOS if necessary
            outputConsole(getDposEposString(value, self.getEPOS(), unit))



    def setTRGS(self, value):
        """
        Define the start of the trigger pulses.
        Expressed in the current units.
        :param value: Start position to trigger the pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convertUnitsToEncoder(value))
        self.sendCommand("TRGS=" + str(value_in_encoder_positions))

    def setTRGW(self, value):
        """
        Define the width of the trigger pulses.
        Expressed in the current units.
        :param value: Width of the trigger pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convertUnitsToEncoder(value))
        self.sendCommand("TRGW=" + str(value_in_encoder_positions))

    def setTRGP(self, value):
        """
        Define the pitch of the trigger pulses.
        Expressed in the current units.
        :param value: Pitch of the trigger pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convertUnitsToEncoder(value))
        self.sendCommand("TRGP=" + str(value_in_encoder_positions))

    def setTRGN(self, value):
        """
        Define the number of trigger pulses.
        :param value: Number of trigger pulses.
        :return:
        """
        self.sendCommand("TRGN=" + str(int(value)))

    def getDPOS(self):
        """
        :return: Return the desired position (DPOS) in the current units.
        """
        return self.convertEncoderUnitsToUnits(self.getData("DPOS"), self.units)

    def getUnit(self):
        """
        :return: Return the current units this stage is working in.
        """
        return self.units

    def step(self, value):
        """
        :param value: The amount it needs to step (specified in the current units)
        If this axis has a rotating stage, this function handles the "wrapping". (Going around in a full circle)
        This function makes use of sendCommand, which blocks the program until the desired position is reached.
        """
        step = self.convertUnitsToEncoder(value, self.units)
        if self.was_valid_DPOS:
            # If the previous DPOS was valid, DPOS is taken as a refrence.
            new_DPOS = int(self.getData("DPOS")) + step
        else:
            new_DPOS = int(self.getData("EPOS")) + step

        if not self.stage.isLineair: # Rotating Stage
            # Below is the amount of encoder units in one revolution.
            # From -180 => +180
            # -180 *(val // 180 % 2) + (val % 180)
            encoderUnitsPerRevolution = self.convertUnitsToEncoder(360, Units.deg)
            new_DPOS = -encoderUnitsPerRevolution/2 * (new_DPOS // (encoderUnitsPerRevolution/2) % 2) + (new_DPOS % (encoderUnitsPerRevolution/2))

        self.setDPOS(new_DPOS, Units.enc, False)  # This is used so position is checked in here.
        if DISABLE_WAITING is False:
            self.__waitForUpdate()  # Waits a couple of updates, so the EPOS is valid and doesn't lagg behind.
            outputConsole("Stepped: " + str(self.convertEncoderUnitsToUnits(step, self.units)) + " " + str(
                self.units) + " " + getDposEposString(self.getDPOS(), self.getEPOS(), self.units))

    def getEPOS(self):
        """
        :return: Returns the EPOS in the correct units this axis is working in.
        """
        return self.convertEncoderUnitsToUnits(self.getData("EPOS"), self.units)

    def setUnits(self, units):
        """
        :param units: The units this axis needs to work in.
        :type units: Units
        """
        self.units = units

    def startLogging(self, increase_poli = True):
        """
        This function starts logging all data that the controller sends.
        It updates the POLI (Polling Interval) to get more data.
        """
        self.isLogging = True
        if increase_poli:
            self.setSetting("POLI", "1")
        self.__waitForUpdate()  # To make sure the POLI is set.
        # DISABLE_WAITING isn't checked here, because it is really necessary.

    def endLogging(self):
        """
        This function stops the logging of all the data.
        It updates the POLI (Polling Interval) back to the default value.
        """
        self.isLogging = False
        logs = self.logs  # Store logs
        self.logs = {}  # Reset logs

        self.setSetting("POLI", str(self.def_poli_value))  # Restore POLI back to default value.
        return logs

    def getFrequency(self):
        return self.getData("FREQ")

    def setSetting(self, tag, value, fromSettingsFile=False, doNotSendThrough=False):
        """
        :param tag: The tag that needs to be stored
        :param value: The value
        :return: None
        This stores the settings in a list as specified in the settings file.
        """

        if fromSettingsFile:
            value = self.applySettingMultipliers(tag, value)
            if "MASS" in tag:
                tag = "CFRQ"
        if "?" not in str(value):
            self.settings.update({tag: value})
        # a change: settings are send when they are set.
        if not doNotSendThrough:
            self.__sendCommand(str(tag) + "=" + str(value))

    def startScan(self, direction, execTime=None):
        """
        :param direction: Positive or negative number.
        :param execTime: Specify the execution time in seconds. If no time is specified, it scans until scanStop() is used.
        :return:
        This function starts a scan.
        A scan is a continous movement with fixed speed. The speed is maintained by closed-loop control.
        A positive number sends the stage towards increasing encoder values.
        A negative number sends the stage towards decreasing encoder values.
        If a time is specified, the scan will go on for that amount of seconds
        If no time is specified, the scan will go on until scanStop() is ran.
        """
        self.__sendCommand("SCAN=" + str(int(direction)))
        self.was_valid_DPOS = False

        if execTime is not None:
            time.sleep(execTime)
            self.__sendCommand("SCAN=0")

    def stopScan(self):
        """
        Stop scanning.
        """
        self.__sendCommand("SCAN=0")
        self.was_valid_DPOS = False

    def setSpeed(self, speed):
        """
        :param speed: The new speed this axis needs to operate on. The speed is specified in the current units/second.
        :type speed: int

        """
        if self.stage.isLineair:
            speed = int(self.convertEncoderUnitsToUnits(self.convertUnitsToEncoder(speed, self.units),
                                                        Units.mu))  # Convert to micrometer
        else:
            speed = self.convertEncoderUnitsToUnits(self.convertUnitsToEncoder(speed, self.units),
                                                    Units.deg)  # Convert to degrees
            speed = int(speed) * 100  # *100 conversion factor.
        self.setSetting("SSPD", str(speed))

    def getSetting(self, tag):
        """
        :param tag: The tag that indicates the setting.
        :return: The value of the setting with the given tag.
        """
        return self.settings.get(tag)

    def setPTOL(self, value):
        """
        :param value: The new value for PTOL (in encoder units!)
        """
        self.setSetting("PTOL", value)

    def setPTO2(self, value):
        """
        :param value: The new value for PTO2 (in encoder units!)
        """
        self.setSetting("PTO2", value)

    def sendCommand(self, command):
        """
        :param command: the command that needs to be send.
        This function is used to let the user send commands.
        If one of the 'setting commands' are used, it is detected.
        This way the settings are saved in self.settings
        """

        tag = command.split("=")[0]
        value = str(command.split("=")[1])

        if tag in NOT_SETTING_COMMANDS:
            self.__sendCommand(command)  # These settings are not stored.
        else:
            self.setSetting(tag, value)  # These settings are stored

    def reset(self):
        """
        Reset this axis.
        """
        self.sendCommand("RSET=0")
        self.was_valid_DPOS = False

    """
        Here all the status bits are checked.
    """

    def isThermalProtection1(self):
        """
        :return: True if the "Thermal Protection 1" flag is set to true.
        """
        return self.__getStatBitAtIndex(2) == "1"

    def isThermalProtection2(self):
        """
        :return: True if the "Thermal Protection 2" flag is set to true.
        """
        return self.__getStatBitAtIndex(3) == "1"

    def isForceZero(self):
        """
        :return: True if the "Force Zero" flag is set to true.
        """
        return self.__getStatBitAtIndex(4) == "1"

    def isMotorOn(self):
        """
        :return: True if the "Motor On" flag is set to true.
        """
        return self.__getStatBitAtIndex(5) == "1"

    def isClosedLoop(self):
        """
        :return: True if the "Closed Loop" flag is set to true.
        """
        return self.__getStatBitAtIndex(6) == "1"

    def isEncoderAtIndex(self):
        """
        :return: True if the "Encoder index" flag is set to true.
        """
        return self.__getStatBitAtIndex(7) == "1"

    def isEncoderValid(self):
        """
        :return: True if the "Encoder Valid" flag is set to true.
        """
        return self.__getStatBitAtIndex(8) == "1"

    def isSearchingIndex(self):
        """
        :return: True if the "Searching index" flag is set to true.
        """
        return self.__getStatBitAtIndex(9) == "1"

    def isPositionReached(self):
        """
        :return: True if the position reached flag is set to true.
        """
        return self.__getStatBitAtIndex(10) == "1"

    def isEncoderError(self):
        """
        :return: True if the "Encoder Error" flag is set to true.
        """
        return self.__getStatBitAtIndex(12) == "1"

    def isScanning(self):
        """
        :return: True if the "Scanning" flag is set to true.
        """
        return self.__getStatBitAtIndex(13) == "1"

    def isAtLeftEnd(self):
        """
        :return: True if the "Left end stop" flag is set to true.
        """
        return self.__getStatBitAtIndex(14) == "1"

    def isAtRightEnd(self):
        """
        :return: True if the "Right end stop" flag is set to true.
        """
        return self.__getStatBitAtIndex(15) == "1"

    def isErrorLimit(self):
        """
        :return: True if the "ErrorLimit" flag is set to true.
        """
        return self.__getStatBitAtIndex(16) == "1"

    def isSearchingOptimalFrequency(self):
        """
        :return: True if the "Searching Optimal Frequency" flag is set to true.
        """
        return self.__getStatBitAtIndex(17) == "1"

    def isSafetyTimeoutTriggered(self):
        """
        :return: True if the "Searching Optimal Frequency" flag is set to true.
        """
        return self.__getStatBitAtIndex(18) == "1"

    def getLetter(self):
        """
        :return: The letter of the axis. If single axis system, it returns "X".
        """
        return self.axis_letter

    def applySettingMultipliers(self, tag, value):
        """
        Some settings have to be multiplied before it can be send to the controller.
        That's done in this function.
        :param tag:     The tag of the setting
        :param value:   The value of the setting
        :return:        Return an adjusted value for this setting.
        """
        # Apply multipliers (different units in settings file and in controller)
        if "MAMP" in tag or "OFSA" in tag or "OFSB" in tag or "AMPL" in tag or "MAM2" in tag:
            # Use amplitude multiplier.
            value = str(int(int(value) * self.stage.amplitudeMultiplier))
        elif "PHAC" in tag or "PHAS" in tag:
            value = str(int(int(value) * self.stage.phaseMultiplier))
        elif "SSPD" in tag or "MSPD" in tag or "ISPD" in tag:  # In the settigns file, SSPD is in mm/s ==> gets translated to mu/s
            value = str(int(float(value) * self.stage.speedMultiplier))
        elif "LLIM" in tag or "RLIM" in tag or "HLIM" in tag:
            # These are given in mm/deg and need to be converted to encoder units
            if self.stage.isLineair:
                value = str(self.convertUnitsToEncoder(value, Units.mm))
            else:
                value = str(self.convertUnitsToEncoder(value, Units.deg))
        elif "POLI" in tag:
            self.def_poli_value = value
        elif "MASS" in tag:
            value = str(self.__massToCFREQ(value))
        elif "ZON1" in tag or "ZON2" in tag:
            if self.stage.isLineair:
                value = str(self.convertUnitsToEncoder(value, Units.mm))
            else:
                value = str(self.convertUnitsToEncoder(value, Units.deg))
        return str(value)

    def __init__(self, xeryon_object, axis_letter, stage):
        """
            Initialize an Axis object.
            :param xeryon_object: This points to the XeryonController object.
            :type xeryon_object: Xeryon
            :param axis_letter: This specifies a specific letter to this axis.
            :type axis_letter: str
            :param stage: This specifies the stage used in this axis.
            :type stage: Stage
        """
        self.axis_letter = axis_letter
        self.xeryon_object = xeryon_object
        self.stage = stage
        self.axis_data = dict({"EPOS": 0, "DPOS": 0, "STAT": 0, "SSPD":0})
        self.settings = dict({})
        if self.stage.isLineair:
            self.units = Units.mm
        else:
            self.units = Units.deg
        # self.settings = self.stage.defaultSettings # Load default settings

    def __massToCFREQ(self, mass):
        """
        Conversion table to change the value of the setting "MASS" into a value for the settings "CFRQ".
        :return:
        """
        mass = int(mass)
        if mass <= 50:
            return 100000
        if mass <= 100:
            return 60000
        if mass <= 250:
            return 30000
        if mass <= 500:
            return 10000
        if mass <= 1000:
            return 5000
        return 3000

    def __str__(self):
        return str(self.axis_letter)

    def __isWithinTol(self, DPOS):
        """
        :param DPOS: The desired position
        :return: True if EPOS is within PTO2 of DPOS. (PTO2 = Position Tolerance 2)
        """
        DPOS = abs(int(DPOS))
        if self.getSetting("PTO2") is not None:
            PTO2 = int(self.getSetting("PTO2"))
        elif self.getSetting("PTOL") is not None:
            PTO2 = int(self.getSetting("PTOL"))
        else:
            PTO2 = 100 #TODO
        EPOS = abs(int(self.getData("EPOS")))

        if DPOS - PTO2 <= EPOS <= DPOS + PTO2:
            return True

    def __timeOutReached(self, start_time, distance):
        """
        :param start_time:  The time the command started in ms.
        :param distance:    The distance the stage needs to travel.
        :return: True if the timeout time has been reached.
        The timeout time is calculated based on the speed (SSPD) and the distance.
        """
        t = getActualTime()
        speed = int(self.getSetting("SSPD"))
        timeout_t = (distance / speed * 1000)  # Convert seconds to milliseconds
        timeout_t *= 1.25  # 25% safety factor

        # For quick and tiny movements, the method above is not accurate.
        # If the timeout_t is smaller than the specified TOUT&TOU2, use TOUT+TOU2
        if self.getSetting("TOUT") is not None:
            TOUT = int(self.getSetting("TOUT"))*3
            if TOUT > timeout_t:
                timeout_t = TOUT

        return (t - start_time) > timeout_t

    def receiveData(self, data):
        """
        :param data: The command that is received.
        :return: None
        This function processes the commands that are send to this axis.
        eg: if "EPOS=5" is send, it stores "EPOS", "5".
        If logging is enabled, this function will store the new incoming data.
        """
        if "=" in data:
            tag = data.split("=")[0]
            val = data.split("=")[1].rstrip("\n\r").replace(" ", "")
            
            if tag not in NOT_SETTING_COMMANDS and "EPOS" not in tag and "DPOS" not in tag and not "FREQ" in tag:  # The received command is a setting that's requested.
                self.setSetting(tag, val)
            elif "FREQ" in tag:
                if self.getSetting("FREQ") is not None and int(self.getSetting("FREQ")) != int(val):
                    self.setSetting("FREQ", val)
            else:
                self.axis_data[tag] = val

            if "STAT" in tag:
                if self.isSafetyTimeoutTriggered():
                    outputConsole("The safety timeout was triggered (TOU2 command). "
                                  "This means that the stage kept moving and oscillating around the desired position. "
                                  "A reset is required now OR 'ENBL=1' should be send.", True)

                if self.isThermalProtection1() or self.isThermalProtection2() or self.isErrorLimit() or self.isSafetyTimeoutTriggered():
                    if self.isErrorLimit():
                        outputConsole("Error limit is reached (status bit 16). A reset is required now OR 'ENBL=1' should be send.", True)

                    if self.isThermalProtection2() or self.isThermalProtection1():
                        outputConsole("Thermal protection 1 or 2 is raised (status bit 2 or 3). A reset is required now OR 'ENBL=1' should be send.", True)
                    
                    if self.isSafetyTimeoutTriggered():
                        outputConsole("Saftety timeout (TOU2 timeout reached) triggered. A reset is required now OR 'ENBL=1' should be send.", True)

                    if AUTO_SEND_ENBL:
                        self.xeryon_object.setMasterSetting("ENBL", "1")
                        outputConsole("'ENBL=1' is automatically send.")

            if "EPOS" in tag:  # This uses "EPOS" as an indicator that a new round of data is coming in.
     
                self.previous_epos.remove(self.previous_epos[0]) # Remove first entry
                self.previous_epos.append(int(self.axis_data["EPOS"])) # Add EPOS: this is like a FIFO list
                self.update_nb += 1  # This update_nb is for the function __waitForUpdate



            if self.isLogging:  # Log all received data if logging is enabled.
                if tag not in ["SRNO", "XLS ", "XRTU", "XLA ", "XTRA", "SOFT", "SYNC"]:  # This data is useless.
                    if self.logs.get(tag) is None:
                        self.logs[tag] = []
                    self.logs[tag].append(int(val))

            if "TIME" in tag:
                # CALCULATE SPEED
                if len(self.previous_time) > 0:
                    self.previous_time.remove(self.previous_time[0])
                if "TIME" in self.axis_data.items():
                    self.previous_time.append(int(self.axis_data["TIME"]))
                if len(self.previous_time) >= 2:
                    t1 = self.previous_time[0]
                    t2 = self.previous_time[1]
                    if int(t2) < int(t1):
                        t2 += 2**16
                
                    if len(self.previous_epos) >= 2:
                        self.axis_data["SSPD"] = (self.previous_epos[1] - self.previous_epos[0])/(t2 - t1)
                
                pass

    def getData(self, TAG):
        """
        :param TAG: The tag requested.
        :return: Returns the value of this tag stored, if no data it returns None.
        eg: get("DPOS") returns the value stored for "DPOS".
        """
        return self.axis_data.get(TAG)  # Returnt zelf None als TAG niet bestaat.

    def sendSettings(self):
        """
        :return: None
        This function sends ALL settings to the controller.
        """
        self.__sendCommand(
            str(self.stage.encoderResolutionCommand))  # This sends: XLS =.. || XRTU=.. || XRTA=.. || XLA =..
        for tag in self.settings:
            self.__sendCommand(str(tag) + "=" + str(self.getSetting(tag)))


    
    def saveSettings(self):
        """
        :return: None
        This function just sends the "AXIS:SAVE" command to store the settings for this axis.
        """
        self.sendCommand("SAVE=0")

    def convertUnitsToEncoder(self, value, units = None):
        """
        :param value: The value that needs to be converted into encoder units.
        :param units: The units the value is in.
        :return: The value converted into encoder units.
        """
        if units is None:
            units = self.units
        value = float(value)
        if units == Units.mm:
            return round(value * 10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.mu:
            return round(value * 10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.nm:
            return round(value * 1 / self.stage.encoderResolution)
        elif units == Units.inch:
            return round(value * 25.4 * 10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.minch:
            return round(value * 25.4 * 10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.enc:
            return round(value)
        elif units == Units.mrad:
            return round(value * 10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.rad:
            return round(value * 10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.deg:
            return round(value * (2 * math.pi) / 360 * 10 ** 6 / self.stage.encoderResolution)
        else:
            self.xeryon_object.stop()
            raise ("Unexpected unit")

    def convertEncoderUnitsToUnits(self, value, units = None):
        """
        :param value: The value (in encoder units) that needs to be converted.
        :param units:  The output unit.
        :return:  The value converted into the output unit.
        """
        if units is None:
            units = self.units
        value = float(value)
        if units == Units.mm:
            return value / (10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.mu:
            return value / (10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.nm:
            return value / (1 / self.stage.encoderResolution)
        elif units == Units.inch:
            return value / (25.4 * 10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.minch:
            return value / (25.4 * 10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.enc:
            return value
        elif units == Units.mrad:
            return value / (10 ** 3 * 1 / self.stage.encoderResolution)
        elif units == Units.rad:
            return value / (10 ** 6 * 1 / self.stage.encoderResolution)
        elif units == Units.deg:
            return value / ((2 * math.pi) / 360 * 10 ** 6 / self.stage.encoderResolution)
        else:
            self.xeryon_object.stop()
            raise ("Unexpected unit")

    def __sendCommand(self, command):
        """
        :param command: The command that needs to be send.
        THIS IS A HIDDEN FUNCTION. Just to make sure that the SETTING commands are send via setSetting() and the other commands via sendCommand()
        This function is used to send a command to the controller.
        No "AXIS:" (e.g.: "X:") needs to be specified, just the command.
        """
        tag = command.split("=")[0]
        value = str(command.split("=")[1])

        prefix = ""  # In a multi axis system, prefix stores the "LETTER:".
        if not self.xeryon_object.isSingleAxisSystem():
            prefix = self.axis_letter + ":"

        # Construct and send the command.
        command = tag + "=" + str(value)
        self.xeryon_object.getCommunication().sendCommand(prefix + command)

    def __waitForUpdate(self):
        """
        This function waits a couple of update messages.
        :return:
        """
        wait_nb = 3  # This number defines how much updates need to be passed.

        # The wait number needs to adjust to POLI.
        if self.getSetting("POLI") is not None:
            wait_nb = wait_nb / int(self.def_poli_value) * int(self.getSetting("POLI"))

        start_nb = int(self.update_nb)
        while (int(self.update_nb) - start_nb) < wait_nb:
            time.sleep(0.01)  # Wait 10 ms

    def __getStatBitAtIndex(self, bit_index):
        if self.getData("STAT") is not None:
            bits = bin(int(self.getData("STAT"))).replace("0b", "")[::-1]
            # [::-1 mirrors the string so the status bit numbering is the same.
            if len(bits) >= bit_index + 1:
                return bits[bit_index]
        return "0"