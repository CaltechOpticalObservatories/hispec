# pylint: skip-file
import time
import math
from .units import Units
from .config import DEFAULT_POLI_VALUE, DISABLE_WAITING, DEBUG_MODE, NOT_SETTING_COMMANDS, AUTO_SEND_ENBL
from .utils import get_dpos_epos_string, get_actual_time
import hispec.util.helper.logger_utils as logger_utils


class Axis:
    axis_letter = None  # Stores the axis letter for this specific axis.
    xeryon_object = None  # Stores the "XeryonController" object.
    axis_data = None  # Stores all the data the controller sends.
    settings = None  # Stores all the settings from the settings file
    stage = None  # Specifies the type of stage used in this axis.
    units = Units.mm  # Specifies the units this axis is currently working in.
    # This number increments each time an update is recieved from the controller.
    update_nb = 0
    # if True, the STEP command takes DPOS as the refrence. It's called "targeted_position=1/0" in the Microcontroller
    was_valid_DPOS = False
    def_poli_value = str(DEFAULT_POLI_VALUE)

    # Stores if this axis is currently "Logging": it's storing its axis_data.
    isLogging = False
    logs = {}  # This stores all the data. It's a dictionary of the form:

    previous_epos = [0, 0]  # Two samples to calculate speed
    previous_time = [0, 0]

    # { "EPOS": [...,...,...], "DPOS": [...,...,...], "STAT":[...,...,...],...}

    def __init__(self, xeryon_object, axis_letter, stage, logger):
        """
            Initialize an Axis object.
            :param xeryon_object: This points to the XeryonController object.
            :type xeryon_object: Xeryon
            :param axis_letter: This specifies a specific letter to this axis.
            :type axis_letter: str
            :param stage: This specifies the stage used in this axis.
            :type stage: Stage
        """
        self.logger = logger
        self.axis_letter = axis_letter
        self.xeryon_object = xeryon_object
        self.stage = stage
        self.axis_data = dict({"EPOS": 0, "DPOS": 0, "STAT": 0, "SSPD": 0})
        self.settings = dict({})
        if self.stage.isLineair:
            self.units = Units.mm
        else:
            self.units = Units.deg
        # self.settings = self.stage.defaultSettings # Load default settings

    def find_index(self, forceWaiting=False, direction=0):
        """
        :return: None
        This function finds the index, after finding the index it goes to the index position.
        It blocks the program until the index is found.
        """
        self.__send_command("INDX=" + str(direction))
        self.was_valid_DPOS = False

        if DISABLE_WAITING is False or forceWaiting is True:
            # Waits a couple of updates, so the EncoderValid flag is valid and doesn't lagg behind.
            self.__wait_for_update()
            self.__wait_for_update()
            self.logger.info("Searching index for axis " + str(self) + ".")
            while not self.is_encoder_valid():  # While index not found, wait.
                if not self.is_searching_index():  # Check if searching for index bit is true.
                    self.logger.info(
                        "Index is not found, but stopped searching for index.", True)
                    break
                time.sleep(0.2)

        if self.is_encoder_valid():
            self.logger.info("Index of axis " + str(self) + " found.")

    def move(self, value):
        value = int(value)
        direction = 0
        if value > 0:
            direction = 1
        elif value < 0:
            direction = -1
        self.send_command("MOVE=" + str(direction))

    def set_D_POS(self, value, differentUnits=None, outputToConsole=True):
        """
        :param value: The new value DPOS has to become.
        :param differentUnits: If the value isn't specified in the current units, specify the correct units.
        :type differentUnits: Units
        :param outputToConsole: Default set to True. If set to False, this function won't output text to the console.
        :return: None
        Note: This function makes use of the send_command function, which is blocking the program until the position is reached.
        """
        unit = self.units  # Current units
        # If the value given are in different units than the current units:
        if differentUnits is not None:
            # Then specify the unit in differentUnits argument.
            unit = differentUnits

        # Convert into encoder units.
        DPOS = int(self.convert_units_to_encoder(value, unit))
        error = False

        self.__send_command("DPOS=" + str(DPOS))
        # And keep it True in order to avoid an accumulating error.
        self.was_valid_DPOS = True

        # Block all futher processes until position is reached.
        # This check isn't nessecary in DEBUG mode or when DISABLE_WAITING is True
        if DEBUG_MODE is False and DISABLE_WAITING is False:
            # send_time = get_actual_time()
            # distance = abs(int(DPOS) - int(self.get_data("EPOS")))  # For calculating timeout time.

            # Wait some updates. This is so the flags (e.g. left end stop) of the previous command aren't received.
            # self.__wait_for_update()

            # Wait until EPOS is within PTO2 AND positionReached status is received.
            while not (self.__is_within_tol(DPOS) and self.is_position_reached()):

                # Check if stage is at left end or right end. ==> out of range movement.
                if self.is_at_left_end() or self.is_at_right_end():
                    self.logger.info("DPOS is out or range. (1) " +
                                   get_dpos_epos_string(value, self.get_EPOS(), unit), True)
                    error = True
                    break

                # # Position reached flag is set, but EPOS not within tolerance of DPOS.
                # if self.is_position_reached() and not self.__is_within_tol(DPOS):
                # # if self.is_position_reached():
                #     # Check if it's a lineair stage and DPOS is beyond it's limits.
                #     if self.stage.isLineair and (
                #             int(self.get_setting("LLIM")) > int(DPOS) or int(self.get_setting("HLIM")) < int(DPOS)):
                #         self.logger.info("DPOS is out or range.(2)" + get_dpos_epos_string(value, self.get_EPOS(), unit), True)
                #         error = True
                #         break

                #     # EPOS is not within tolerance of DPOS, unknown reason.
                #     self.logger.info("Position not reached. (3) " + get_dpos_epos_string(value, self.get_EPOS(), unit), True)
                #     error = True
                #     break

                if self.is_encoder_error():
                    self.logger.info(
                        "Position not reached. (4). Encoder gave an error.", True)
                    error = True
                    break

                if self.is_error_limit():
                    self.logger.info(
                        "Position not reached. (5) ELIM Triggered.", True)
                    error = True
                    break

                if self.is_safety_timeout_triggered():
                    self.logger.info(
                        "Position not reached. (6) TOU2 (Timeout 2) triggered.", True)
                    error = True
                    break

                if self.is_thermal_protection_1() or self.is_thermal_protection_2():
                    self.logger.info(
                        "Position not reached. (7) amplifier error.", True)
                    error = True
                    break

                # # This movement took too long, timeout time is estimated with speed & distance.
                # if self.__time_out_reached(send_time, distance):
                #     self.logger.info(
                #         "Position not reached, timeout reached. (4) " + get_dpos_epos_string(value, self.get_EPOS(), unit),
                #         True)
                #     error = True
                #     break
                # Keep polling ==> if timeout is not done, the computer will poll too fast. The microcontroller can't follow.

                time.sleep(0.01)

        if outputToConsole and error is False and DISABLE_WAITING is False:  # Output new DPOS & EPOS if necessary
            self.logger.info(get_dpos_epos_string(value, self.get_EPOS(), unit))

    def set_TRGS(self, value):
        """
        Define the start of the trigger pulses.
        Expressed in the current units.
        :param value: Start position to trigger the pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convert_units_to_encoder(value))
        self.send_command("TRGS=" + str(value_in_encoder_positions))

    def set_TRGW(self, value):
        """
        Define the width of the trigger pulses.
        Expressed in the current units.
        :param value: Width of the trigger pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convert_units_to_encoder(value))
        self.send_command("TRGW=" + str(value_in_encoder_positions))

    def set_TRGP(self, value):
        """
        Define the pitch of the trigger pulses.
        Expressed in the current units.
        :param value: Pitch of the trigger pulses. Expressed in the current units.
        :return:
        """
        value_in_encoder_positions = int(self.convert_units_to_encoder(value))
        self.send_command("TRGP=" + str(value_in_encoder_positions))

    def set_TRGN(self, value):
        """
        Define the number of trigger pulses.
        :param value: Number of trigger pulses.
        :return:
        """
        self.send_command("TRGN=" + str(int(value)))

    def get_DPOS(self):
        """
        :return: Return the desired position (DPOS) in the current units.
        """
        return self.convert_encoder_units_to_units(self.get_data("DPOS"), self.units)

    def get_unit(self):
        """
        :return: Return the current units this stage is working in.
        """
        return self.units

    def step(self, value):
        """
        :param value: The amount it needs to step (specified in the current units)
        If this axis has a rotating stage, this function handles the "wrapping". (Going around in a full circle)
        This function makes use of send_command, which blocks the program until the desired position is reached.
        """
        step = self.convert_units_to_encoder(value, self.units)
        if self.was_valid_DPOS:
            # If the previous DPOS was valid, DPOS is taken as a refrence.
            new_DPOS = int(self.get_data("DPOS")) + step
        else:
            new_DPOS = int(self.get_data("EPOS")) + step

        if not self.stage.isLineair:  # Rotating Stage
            # Below is the amount of encoder units in one revolution.
            # From -180 => +180
            # -180 *(val // 180 % 2) + (val % 180)
            encoderUnitsPerRevolution = self.convert_units_to_encoder(
                360, Units.deg)
            new_DPOS = -encoderUnitsPerRevolution/2 * \
                (new_DPOS // (encoderUnitsPerRevolution/2) %
                 2) + (new_DPOS % (encoderUnitsPerRevolution/2))

        # This is used so position is checked in here.
        self.set_D_POS(new_DPOS, Units.enc, False)
        if DISABLE_WAITING is False:
            # Waits a couple of updates, so the EPOS is valid and doesn't lagg behind.
            self.__wait_for_update()
            self.logger.info("Stepped: " + str(self.convert_encoder_units_to_units(step, self.units)) + " " + str(
                self.units) + " " + get_dpos_epos_string(self.getDPOS(), self.get_EPOS(), self.units))

    def get_EPOS(self):
        """
        :return: Returns the EPOS in the correct units this axis is working in.
        """
        return self.convert_encoder_units_to_units(self.get_data("EPOS"), self.units)

    def set_units(self, units):
        """
        :param units: The units this axis needs to work in.
        :type units: Units
        """
        self.units = units

    def start_logging(self, increase_poli=True):
        """
        This function starts logging all data that the controller sends.
        It updates the POLI (Polling Interval) to get more data.
        """
        self.isLogging = True
        if increase_poli:
            self.set_setting("POLI", "1")
        self.__wait_for_update()  # To make sure the POLI is set.
        # DISABLE_WAITING isn't checked here, because it is really necessary.

    def end_logging(self):
        """
        This function stops the logging of all the data.
        It updates the POLI (Polling Interval) back to the default value.
        """
        self.isLogging = False
        logs = self.logs  # Store logs
        self.logs = {}  # Reset logs

        # Restore POLI back to default value.
        self.set_setting("POLI", str(self.def_poli_value))
        return logs

    def get_frequency(self):
        return self.get_data("FREQ")

    def set_setting(self, tag, value, fromSettingsFile=False, doNotSendThrough=False):
        """
        :param tag: The tag that needs to be stored
        :param value: The value
        :return: None
        This stores the settings in a list as specified in the settings file.
        """

        if fromSettingsFile:
            value = self.apply_setting_multipliers(tag, value)
            if "MASS" in tag:
                tag = "CFRQ"
        if "?" not in str(value):
            self.settings.update({tag: value})
        # a change: settings are send when they are set.
        if not doNotSendThrough:
            self.__send_command(str(tag) + "=" + str(value))

    def start_scan(self, direction, execTime=None):
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
        self.__send_command("SCAN=" + str(int(direction)))
        self.was_valid_DPOS = False

        if execTime is not None:
            time.sleep(execTime)
            self.__send_command("SCAN=0")

    def stop_scan(self):
        """
        Stop scanning.
        """
        self.__send_command("SCAN=0")
        self.was_valid_DPOS = False

    def set_speed(self, speed):
        """
        :param speed: The new speed this axis needs to operate on. The speed is specified in the current units/second.
        :type speed: int

        """
        if self.stage.isLineair:
            speed = int(self.convert_encoder_units_to_units(self.convert_units_to_encoder(speed, self.units),
                                                            Units.mu))  # Convert to micrometer
        else:
            speed = self.convert_encoder_units_to_units(self.convert_units_to_encoder(speed, self.units),
                                                        Units.deg)  # Convert to degrees
            speed = int(speed) * 100  # *100 conversion factor.
        self.set_setting("SSPD", str(speed))

    def get_setting(self, tag):
        """
        :param tag: The tag that indicates the setting.
        :return: The value of the setting with the given tag.
        """
        return self.settings.get(tag)

    def set_PTOL(self, value):
        """
        :param value: The new value for PTOL (in encoder units!)
        """
        self.set_setting("PTOL", value)

    def set_PTO2(self, value):
        """
        :param value: The new value for PTO2 (in encoder units!)
        """
        self.set_setting("PTO2", value)

    def send_command(self, command):
        """
        :param command: the command that needs to be send.
        This function is used to let the user send commands.
        If one of the 'setting commands' are used, it is detected.
        This way the settings are saved in self.settings
        """

        tag = command.split("=")[0]
        value = str(command.split("=")[1])

        if tag in NOT_SETTING_COMMANDS:
            self.__send_command(command)  # These settings are not stored.
        else:
            self.set_setting(tag, value)  # These settings are stored

    def reset(self):
        """
        Reset this axis.
        """
        self.send_command("RSET=0")
        self.was_valid_DPOS = False

    """
        Here all the status bits are checked.
    """

    def is_thermal_protection_1(self):
        """
        :return: True if the "Thermal Protection 1" flag is set to true.
        """
        return self.__get_stat_bit_at_index(2) == "1"

    def is_thermal_protection_2(self):
        """
        :return: True if the "Thermal Protection 2" flag is set to true.
        """
        return self.__get_stat_bit_at_index(3) == "1"

    def is_force_zero(self):
        """
        :return: True if the "Force Zero" flag is set to true.
        """
        return self.__get_stat_bit_at_index(4) == "1"

    def is_motor_on(self):
        """
        :return: True if the "Motor On" flag is set to true.
        """
        return self.__get_stat_bit_at_index(5) == "1"

    def is_closed_loop(self):
        """
        :return: True if the "Closed Loop" flag is set to true.
        """
        return self.__get_stat_bit_at_index(6) == "1"

    def is_encoder_at_index(self):
        """
        :return: True if the "Encoder index" flag is set to true.
        """
        return self.__get_stat_bit_at_index(7) == "1"

    def is_encoder_valid(self):
        """
        :return: True if the "Encoder Valid" flag is set to true.
        """
        return self.__get_stat_bit_at_index(8) == "1"

    def is_searching_index(self):
        """
        :return: True if the "Searching index" flag is set to true.
        """
        return self.__get_stat_bit_at_index(9) == "1"

    def is_position_reached(self):
        """
        :return: True if the position reached flag is set to true.
        """
        return self.__get_stat_bit_at_index(10) == "1"

    def is_encoder_error(self):
        """
        :return: True if the "Encoder Error" flag is set to true.
        """
        return self.__get_stat_bit_at_index(12) == "1"

    def is_scanning(self):
        """
        :return: True if the "Scanning" flag is set to true.
        """
        return self.__get_stat_bit_at_index(13) == "1"

    def is_at_left_end(self):
        """
        :return: True if the "Left end stop" flag is set to true.
        """
        return self.__get_stat_bit_at_index(14) == "1"

    def is_at_right_end(self):
        """
        :return: True if the "Right end stop" flag is set to true.
        """
        return self.__get_stat_bit_at_index(15) == "1"

    def is_error_limit(self):
        """
        :return: True if the "ErrorLimit" flag is set to true.
        """
        return self.__get_stat_bit_at_index(16) == "1"

    def is_searching_optimal_frequency(self):
        """
        :return: True if the "Searching Optimal Frequency" flag is set to true.
        """
        return self.__get_stat_bit_at_index(17) == "1"

    def is_safety_timeout_triggered(self):
        """
        :return: True if the "Searching Optimal Frequency" flag is set to true.
        """
        return self.__get_stat_bit_at_index(18) == "1"

    def get_letter(self):
        """
        :return: The letter of the axis. If single axis system, it returns "X".
        """
        return self.axis_letter

    def apply_setting_multipliers(self, tag, value):
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
        # In the settigns file, SSPD is in mm/s ==> gets translated to mu/s
        elif "SSPD" in tag or "MSPD" in tag or "ISPD" in tag:
            value = str(int(float(value) * self.stage.speedMultiplier))
        elif "LLIM" in tag or "RLIM" in tag or "HLIM" in tag:
            # These are given in mm/deg and need to be converted to encoder units
            if self.stage.isLineair:
                value = str(self.convert_units_to_encoder(value, Units.mm))
            else:
                value = str(self.convert_units_to_encoder(value, Units.deg))
        elif "POLI" in tag:
            self.def_poli_value = value
        elif "MASS" in tag:
            value = str(self.__mass_to_CFREQ(value))
        elif "ZON1" in tag or "ZON2" in tag:
            if self.stage.isLineair:
                value = str(self.convert_units_to_encoder(value, Units.mm))
            else:
                value = str(self.convert_units_to_encoder(value, Units.deg))
        return str(value)

    def __mass_to_CFREQ(self, mass):
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

    def __is_within_tol(self, DPOS):
        """
        :param DPOS: The desired position
        :return: True if EPOS is within PTO2 of DPOS. (PTO2 = Position Tolerance 2)
        """
        DPOS = abs(int(DPOS))
        if self.get_setting("PTO2") is not None:
            PTO2 = int(self.get_setting("PTO2"))
        elif self.get_setting("PTOL") is not None:
            PTO2 = int(self.get_setting("PTOL"))
        else:
            PTO2 = 100  # TODO
        EPOS = abs(int(self.get_data("EPOS")))

        if DPOS - PTO2 <= EPOS <= DPOS + PTO2:
            return True

    def __time_out_reached(self, start_time, distance):
        """
        :param start_time:  The time the command started in ms.
        :param distance:    The distance the stage needs to travel.
        :return: True if the timeout time has been reached.
        The timeout time is calculated based on the speed (SSPD) and the distance.
        """
        t = get_actual_time()
        speed = int(self.get_setting("SSPD"))
        # Convert seconds to milliseconds
        timeout_t = (distance / speed * 1000)
        timeout_t *= 1.25  # 25% safety factor

        # For quick and tiny movements, the method above is not accurate.
        # If the timeout_t is smaller than the specified TOUT&TOU2, use TOUT+TOU2
        if self.get_setting("TOUT") is not None:
            TOUT = int(self.get_setting("TOUT"))*3
            if TOUT > timeout_t:
                timeout_t = TOUT

        return (t - start_time) > timeout_t

    def receive_data(self, data):
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

            # The received command is a setting that's requested.
            if tag not in NOT_SETTING_COMMANDS and "EPOS" not in tag and "DPOS" not in tag and not "FREQ" in tag:
                self.set_setting(tag, val)
            elif "FREQ" in tag:
                if self.get_setting("FREQ") is not None and int(self.get_setting("FREQ")) != int(val):
                    self.set_setting("FREQ", val)
            else:
                self.axis_data[tag] = val

            if "STAT" in tag:
                if self.is_safety_timeout_triggered():
                    self.logger.info("The safety timeout was triggered (TOU2 command). "
                                   "This means that the stage kept moving and oscillating around the desired position. "
                                   "A reset is required now OR 'ENBL=1' should be send.", True)

                if self.is_thermal_protection_1() or self.is_thermal_protection_2() or self.is_error_limit() or self.is_safety_timeout_triggered():
                    if self.is_error_limit():
                        self.logger.info(
                            "Error limit is reached (status bit 16). A reset is required now OR 'ENBL=1' should be send.", True)

                    if self.is_thermal_protection_2() or self.is_thermal_protection_1():
                        self.logger.info(
                            "Thermal protection 1 or 2 is raised (status bit 2 or 3). A reset is required now OR 'ENBL=1' should be send.", True)

                    if self.is_safety_timeout_triggered():
                        self.logger.info(
                            "Saftety timeout (TOU2 timeout reached) triggered. A reset is required now OR 'ENBL=1' should be send.", True)

                    if AUTO_SEND_ENBL:
                        self.xeryon_object.set_master_setting("ENBL", "1")
                        self.logger.info("'ENBL=1' is automatically send.")

            if "EPOS" in tag:  # This uses "EPOS" as an indicator that a new round of data is coming in.

                self.previous_epos.remove(
                    self.previous_epos[0])  # Remove first entry
                # Add EPOS: this is like a FIFO list
                self.previous_epos.append(int(self.axis_data["EPOS"]))
                self.update_nb += 1  # This update_nb is for the function __wait_for_update

            if self.isLogging:  # Log all received data if logging is enabled.
                # This data is useless.
                if tag not in ["SRNO", "XLS ", "XRTU", "XLA ", "XTRA", "SOFT", "SYNC"]:
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
                        self.axis_data["SSPD"] = (
                            self.previous_epos[1] - self.previous_epos[0])/(t2 - t1)

                pass

    def get_data(self, TAG):
        """
        :param TAG: The tag requested.
        :return: Returns the value of this tag stored, if no data it returns None.
        eg: get("DPOS") returns the value stored for "DPOS".
        """
        return self.axis_data.get(TAG)  # Returnt zelf None als TAG niet bestaat.

    def send_settings(self):
        """
        :return: None
        This function sends ALL settings to the controller.
        """
        self.__send_command(
            str(self.stage.encoderResolutionCommand))  # This sends: XLS =.. || XRTU=.. || XRTA=.. || XLA =..
        for tag in self.settings:
            self.__send_command(str(tag) + "=" + str(self.get_setting(tag)))

    def save_settings(self):
        """
        :return: None
        This function just sends the "AXIS:SAVE" command to store the settings for this axis.
        """
        self.send_command("SAVE=0")

    def convert_units_to_encoder(self, value, units=None):
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

    def convert_encoder_units_to_units(self, value, units=None):
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

    def __send_command(self, command):
        """
        :param command: The command that needs to be send.
        THIS IS A HIDDEN FUNCTION. Just to make sure that the SETTING commands are send via set_setting() and the other commands via send_command()
        This function is used to send a command to the controller.
        No "AXIS:" (e.g.: "X:") needs to be specified, just the command.
        """
        tag = command.split("=")[0]
        value = str(command.split("=")[1])

        prefix = ""  # In a multi axis system, prefix stores the "LETTER:".
        if not self.xeryon_object.is_single_axis_system():
            prefix = self.axis_letter + ":"

        # Construct and send the command.
        command = tag + "=" + str(value)
        self.xeryon_object.get_communication().send_command(prefix + command)

    def __wait_for_update(self):
        """
        This function waits a couple of update messages.
        :return:
        """
        wait_nb = 3  # This number defines how much updates need to be passed.

        # The wait number needs to adjust to POLI.
        if self.get_setting("POLI") is not None:
            wait_nb = wait_nb / int(self.def_poli_value) * \
                int(self.get_setting("POLI"))

        start_nb = int(self.update_nb)
        while (int(self.update_nb) - start_nb) < wait_nb:
            time.sleep(0.01)  # Wait 10 ms

    def __get_stat_bit_at_index(self, bit_index):
        if self.get_data("STAT") is not None:
            bits = bin(int(self.get_data("STAT"))).replace("0b", "")[::-1]
            # [::-1 mirrors the string so the status bit numbering is the same.
            if len(bits) >= bit_index + 1:
                return bits[bit_index]
        return "0"
