#ifndef _SPCE_H 
#define _SPCE_H


#define MAX_COMMAND_LENGTH		64
#define MAX_CODE_LENGTH			3
#define MAX_RESPONSE_LENGTH		100
#define SPCE_BUS_ADDRESS		1
#define SPCE_COMM_INTERFACE		0	/* RS232 */
#define SPCE_PUMP_SIZE			3	/* Pump Size in L/s */
#define SPCE_ARC_DETECT		1	/* Arc Detect ON */
#define SPCE_HV_AUTO_RECOVERY		0	/* HV auto recover OFF */
#define SPCE_AUTO_RESTART		1	/* Pump auto restart ON */
#define SPCE_COMM_MODE			2	/* Comm mode is FULL (for now)*/
#define SPCE_TIME_BETWEEN_COMMANDS	120000	/* microsecs */
#define SPCE_START_CHAR		'~'
#define SPCE_UNITS_TORR		'T'
#define SPCE_UNITS_MBAR		'M'
#define SPCE_UNITS_PASCAL		'P'
#define SPCE_KEYPAD_UNLOCK		0
#define SPCE_KEYPAD_LOCK		1

/* Spce baud rate and parity */
#define	SPCE_BAUD_RATE		9600
#define SPCE_PARITY		(int)'N'

#define SPCE_QUERY				1
#define SPCE_COMMAND				0
#define SPCE_TURNS_OFF_ABOVE			0
#define SPCE_TURNS_ON_BELOW			1

/* Spce command codes */
#define SPCE_COMMAND_READ_MODEL		0x01	/* not implemented */
#define SPCE_COMMAND_READ_VERSION		0x02
#define SPCE_COMMAND_RESET			0x07
#define SPCE_COMMAND_SET_ARC_DETECT		0x91
#define SPCE_COMMAND_GET_ARC_DETECT		0x92
#define SPCE_COMMAND_READ_CURRENT		0x0a
#define SPCE_COMMAND_READ_PRESSURE		0x0b
#define SPCE_COMMAND_READ_VOLTAGE		0x0c
#define SPCE_COMMAND_GET_SUPPLY_STATUS		0x0d	/* not implemented */
#define SPCE_COMMAND_SET_PRESS_UNITS		0x0e
#define SPCE_COMMAND_GET_PUMP_SIZE		0x11
#define SPCE_COMMAND_SET_PUMP_SIZE		0x12
#define SPCE_COMMAND_GET_CAL_FACTOR		0x1d
#define SPCE_COMMAND_SET_CAL_FACTOR		0x1e
#define SPCE_COMMAND_SET_AUTO_RESTART		0x33
#define SPCE_COMMAND_GET_AUTO_RESTART		0x34
#define SPCE_COMMAND_START_PUMP		0x37
#define SPCE_COMMAND_STOP_PUMP			0x38
#define SPCE_COMMAND_GET_SETPOINT		0x3c	/* not implemented */
#define SPCE_COMMAND_SET_SETPOINT		0x3d	/* not implemented */
#define SPCE_COMMAND_LOCK_KEYPAD		0x44
#define SPCE_COMMAND_UNLOCK_KEYPAD		0x45
#define SPCE_COMMAND_GET_ANALOG_MODE		0x50
#define SPCE_COMMAND_SET_ANALOG_MODE		0x51
#define SPCE_COMMAND_IS_HIGH_VOLTAGE_ON	0x61
#define SPCE_COMMAND_SET_SERIAL_ADDRESS	0x62	/* not implemented */
#define SPCE_COMMAND_SET_HV_AUTORECOVERY	0x68
#define SPCE_COMMAND_GET_HV_AUTORECOVERY	0x69
#define SPCE_COMMAND_SET_FIRMWARE_UPDATE	0x8f	/* not implemented */
#define SPCE_COMMAND_SET_COMM_MODE		0xd3
#define SPCE_COMMAND_GET_COMM_MODE		0xd4
#define SPCE_COMMAND_GETSET_SERIAL_COMM	0x46	/* not implemented */
#define SPCE_COMMAND_GETSET_ETHERNET_IP	0x47	/* not implemented */
#define SPCE_COMMAND_GETSET_ETHERNET_MASK	0x48	/* not implemented */
#define SPCE_COMMAND_GETSET_ETHERNET_GTWY	0x49	/* not implemented */
#define SPCE_COMMAND_GET_ETHERNET_MAC		0x4a	/* not implemented */
#define SPCE_COMMAND_SET_COMM_INTERFACE	0x4b
#define SPCE_COMMAND_INITIATE_FEA		0x4c	/* not implemented */
#define SPCE_COMMAND_GET_FEA_DATA		0x4d	/* not implemented */
#define SPCE_COMMAND_INITIATE_HIPOT		0x52	/* not implemented */
#define SPCE_COMMAND_GETSET_HIPOT_TARGET	0x53	/* not implemented */
#define SPCE_COMMAND_GETSET_FOLDBACK_VOLTS	0x54	/* not implemented */
#define SPCE_COMMAND_GETSET_FOLDBACK_PRES	0x55	/* not implemented */
#define SPCE_COMMAND_MAX 0x92

/* Spce error codes */
#define SPCE_ERROR_CODE0			-500
#define SPCE_ERROR_BAD_COMMAND_CODE		SPCE_ERROR_CODE0 - 1
#define SPCE_ERROR_UNKNOWN_COMMAND_CODE	SPCE_ERROR_CODE0 - 2
#define SPCE_ERROR_BAD_CHECKSUM		SPCE_ERROR_CODE0 - 3
#define SPCE_ERROR_TIMEOUT			SPCE_ERROR_CODE0 - 4
#define SPCE_ERROR_UNKNOWN_ERROR		SPCE_ERROR_CODE0 - 6
#define SPCE_ERROR_COMM_ERROR			SPCE_ERROR_CODE0 - 7
#define SPCE_ERROR_OPEN_PORT			SPCE_ERROR_CODE0 - 10
#define SPCE_ERROR_CLOSE_PORT			SPCE_ERROR_CODE0 - 11
#define SPCE_ERROR_CONFIG_PORT			SPCE_ERROR_CODE0 - 12
#define SPCE_ERROR_WRITE_COMMAND		SPCE_ERROR_CODE0 - 13
#define SPCE_ERROR_READ_COMMAND		SPCE_ERROR_CODE0 - 14
#define SPCE_ERROR_INVALID_RESPONSE		SPCE_ERROR_CODE0 - 15
#define SPCE_ERROR_BAD_RESPONSE_CHECKSUM	SPCE_ERROR_CODE0 - 16
#define SPCE_ERROR_VALUE_OUT_OF_RANGE		SPCE_ERROR_CODE0 - 17

#define SPCE_ERROR_MAX 18

/* Spce display codes */
#define SPCE_DISPLAY_CODE0			-400
#define SPCE_DISPLAY_COOLDOWN_CYCLES		SPCE_DISPLAY_CODE0 - 1
#define SPCE_DISPLAY_VACUUM_LOSS		SPCE_DISPLAY_CODE0 - 2
#define SPCE_DISPLAY_SHORT_CIRCUIT		SPCE_DISPLAY_CODE0 - 3
#define SPCE_DISPLAY_EXCESS_PRESSURE		SPCE_DISPLAY_CODE0 - 4
#define SPCE_DISPLAY_PUMP_OVERLOAD		SPCE_DISPLAY_CODE0 - 5
#define SPCE_DISPLAY_SUPPLY_POWER		SPCE_DISPLAY_CODE0 - 6
#define SPCE_DISPLAY_START_UNDER_VOLTAGE	SPCE_DISPLAY_CODE0 - 7
#define SPCE_DISPLAY_PUMP_IS_ARCING		SPCE_DISPLAY_CODE0 - 10
#define SPCE_DISPLAY_THERMAL_RUNAWAY		SPCE_DISPLAY_CODE0 - 12
#define SPCE_DISPLAY_UNKNOWN_ERROR		SPCE_DISPLAY_CODE0 - 19
#define SPCE_DISPLAY_SAFE_CONN_INTERLOCK	SPCE_DISPLAY_CODE0 - 20
#define SPCE_DISPLAY_HVE_INTERLOCK		SPCE_DISPLAY_CODE0 - 21
#define SPCE_DISPLAY_SET_PUMP_SIZE		SPCE_DISPLAY_CODE0 - 22
#define SPCE_DISPLAY_CALIBRATION_NEEDED	SPCE_DISPLAY_CODE0 - 23
#define SPCE_DISPLAY_RESET_REQUIRED		SPCE_DISPLAY_CODE0 - 24
#define SPCE_DISPLAY_TEMPERATURE_WARNING	SPCE_DISPLAY_CODE0 - 25
#define SPCE_DISPLAY_SUPPLY_OVERHEAT		SPCE_DISPLAY_CODE0 - 26
#define SPCE_DISPLAY_CURRENT_LIMITED		SPCE_DISPLAY_CODE0 - 27
#define SPCE_DISPLAY_INTERNAL_BUS_ERROR	SPCE_DISPLAY_CODE0 - 30
#define SPCE_DISPLAY_HV_CONTROL_ERROR		SPCE_DISPLAY_CODE0 - 31
#define SPCE_DISPLAY_CURRENT_CONTROL_ERROR	SPCE_DISPLAY_CODE0 - 32
#define SPCE_DISPLAY_CURRENT_MEASURE_ERROR	SPCE_DISPLAY_CODE0 - 33
#define SPCE_DISPLAY_VOLTAGE_CONTROL_ERROR	SPCE_DISPLAY_CODE0 - 34
#define SPCE_DISPLAY_VOLTAGE_MEASURE_ERROR	SPCE_DISPLAY_CODE0 - 35
#define SPCE_DISPLAY_POLARITY_MISMATCH		SPCE_DISPLAY_CODE0 - 36
#define SPCE_DISPLAY_HV_NOT_INSTALLED		SPCE_DISPLAY_CODE0 - 37
#define SPCE_DISPLAY_INPUT_VOLTAGE_ERROR	SPCE_DISPLAY_CODE0 - 38

#define SPCE_DISPLAY_MAX 48

/* Spce data response length */
#define SPCE_PRESSURE_DATA_SIZE		13
#define SPCE_RESPONSE_DATA_SIZE		13

#ifdef CREATOR
char *SpceErrMsg[] = {
  NULL,
  "SPCe Error (01): Command code/format is not correct, semantics is wrong.",
  "SPCe Error (02): Command code not recognized, does not exist.",
  "SPCe Error (03): Bad checksum.",
  "SPCe Error (04): Command timeout.",
  NULL,
  "SPCe Error (06): Firmware encountered an unknown error.",
  "SPCe Error (07): Communication error, zero characters recieved.",
  NULL,
  NULL,
  "SPCe Error (10): Socket port open error.",
  "SPCe Error (11): Socket port close error.",
  "SPCe Error (12): Socket port configuration error.",
  "SPCe Error (13): Socket port write error.",
  "SPCe Error (14): Socket port read error.",
  "SPCe Error (15): Invalid response.",
  "SPCe Error (16): Bad response checksum.",
  "SPCe Error (17): Value out of range.",
NULL
};
#else
extern char *SpceErrMsg[];
#endif

#ifdef CREATOR
char *SpceDspMsg[] = {
  NULL,
  "SPCe Error (01): Too many cooldown cycles (>3) occured during pump starting.",
  "SPCe Error (02): The voltage dropped below 1200V while pump was running.",
  "SPCe Error (03): Short circuit condition has been detected during pump starting.",
  "SPCe Error (04): Excessive pressure condition detected.  Pressure greater than 1.0e-4 Torr detected.",
  "SPCe Error (05): Too much power delivered to the pump for the given pump size.",
  "SPCe Error (06): Supply output power detected greater than 50W.",
  "SPCe Error (07): The voltage did not reach 2000V within the maximum pump starting time of 5 minutes.",
  NULL,
  NULL,
  "SPCe Error (10): Arcing detected.",
  NULL,
  "SPCe Error (12): Significant drop in voltage detected during pump starting.",
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  "SPCe Error (19): Unknown Error.",
  "SPCe Error (20): Safety interlock connection is not detected.  Check safe-conn connection.",
  "SPCe Error (21): HVE interlock set or HVE Signal off.",
  "SPCe Error (22): Pump size is not set.",
  "SPCe Error (23): Supply calibration has not been performed.  Required for accurate current/pressure readings.",
  "SPCe Error (24): Supply calibration parameters are outside normal ranges.  System reset will clear all paramters to factory defaults.",
  "SPCe Error (25): Supply internal temperature is past the threshold.",
  "SPCe Error (26): Supply internal temperature too high. HV operation is disabled.",
  "SPCe Error (27): Supply current is limited.  The limit is set by programming the pump size or manually by the user.",
  NULL,
  NULL,
  "SPCe Error (30): Internal data bus error detected.",
  "SPCe Error (31): Supply HV control mechanism malfunctioning.  On/Off state is malfunctioning.",
  "SPCe Error (32): Supply current control mechanism malfunctioning.",
  "SPCe Error (33): Supply current measuring mechanism malfunctioning.",
  "SPCe Error (34): Supply HV control mechanism malfunctioning.  Voltage output level is malfunctioning.",
  "SPCe Error (35): Supply voltage measuring mechanism malfunctioning.",
  "SPCe Error (36): Internal boards polarity mismatch.",
  "SPCe Error (37): HV module missing.",
  "SPCe Error (38): Input power voltage outside 22-26VDC range.  HV operation disabled.",
  NULL,
  "SPCe Error (40): Socket port open error.",
  "SPCe Error (41): Socket port close error.",
  "SPCe Error (42): Socket port configuration error.",
  "SPCe Error (43): Socket port write error.",
  "SPCe Error (44): Socket port read error.",
NULL
};
#else
extern char *SpceDspMsg[];
#endif

/* function prototypes */
int spce_read_version(char *port, char *version);
int spce_reset(char *port);
int spce_set_arc_detect(char *port, int yesno);
int spce_get_arc_detect(char *port, int *yesno);
int spce_read_current(char *port, float *outcurrent);
int spce_read_pressure(char *port, float *outpressure); 
int spce_read_voltage(char *port, int *outvoltage);
int spce_set_units(char *port, int units);
int spce_get_pump_size(char *port, int *outsize);
int spce_set_pump_size(char *port, int size);
int spce_get_cal_factor(char *port, float *outcalfact);
int spce_set_cal_factor(char *port, float calfact);
int spce_set_auto_restart(char *port, int yesno);
int spce_get_auto_restart(char *port, int *yesno);
int spce_pump_start(char *port);
int spce_pump_stop(char *port);
int spce_lock_keypad(char *port, int lock);
int spce_get_analog_mode(char *port, int *outmode);
int spce_set_analog_mode(char *port, int mode);
int spce_high_voltage_on(char *port, int *yesno);
int spce_set_hv_autorecovery(char *port, int mode);
int spce_get_hv_autorecovery(char *port, int *outmode);
int spce_set_comm_mode(char *port, int mode);
int spce_get_comm_mode(char *port, int *outmode);
int spce_set_comm_interface(char *port, int interface);
int spce_send_command(char *port, char *cmd);
int spce_send_request(char *port, char *cmd, char *response);
int spce_create_command_string(char *outstring, int bus_address, 
				int command_code, char *command_data,
				int do_checksum);
int spce_validate_response(char *response, int command_code);
float getFloatFromSpceResponse(char *response);
int getStringFromSpceResponse(char *response, char *outstring);
float getIntFromSpceResponse(char *response);

#endif  /* _KPRS_SPCE_H */
