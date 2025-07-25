#ifndef _KPRS_GAMMA_H 
#define _KPRS_GAMMA_H


#define MAX_COMMAND_LENGTH		64
#define MAX_CODE_LENGTH			3
#define MAX_RESPONSE_LENGTH		100
#define GAMMA_BUS_ADDRESS		1
#define GAMMA_COMM_INTERFACE		0	/* RS232 */
#define GAMMA_PUMP_SIZE			3	/* Pump Size in L/s */
#define GAMMA_ARC_DETECT		1	/* Arc Detect ON */
#define GAMMA_HV_AUTO_RECOVERY		0	/* HV auto recover OFF */
#define GAMMA_AUTO_RESTART		1	/* Pump auto restart ON */
#define GAMMA_COMM_MODE			2	/* Comm mode is FULL (for now)*/
#define GAMMA_TIME_BETWEEN_COMMANDS	120000	/* microsecs */
#define GAMMA_START_CHAR		'~'
#define GAMMA_UNITS_TORR		'T'
#define GAMMA_UNITS_MBAR		'M'
#define GAMMA_UNITS_PASCAL		'P'
#define GAMMA_KEYPAD_UNLOCK		0
#define GAMMA_KEYPAD_LOCK		1

/* Gamma baud rate and parity */
#define	GAMMA_BAUD_RATE		9600
#define GAMMA_PARITY		(int)'N'

#define GAMMA_QUERY				1
#define GAMMA_COMMAND				0
#define GAMMA_TURNS_OFF_ABOVE			0
#define GAMMA_TURNS_ON_BELOW			1

/* Gamma command codes */
#define GAMMA_COMMAND_READ_MODEL		0x01	/* not implemented */
#define GAMMA_COMMAND_READ_VERSION		0x02
#define GAMMA_COMMAND_RESET			0x07
#define GAMMA_COMMAND_SET_ARC_DETECT		0x91
#define GAMMA_COMMAND_GET_ARC_DETECT		0x92
#define GAMMA_COMMAND_READ_CURRENT		0x0a
#define GAMMA_COMMAND_READ_PRESSURE		0x0b
#define GAMMA_COMMAND_READ_VOLTAGE		0x0c
#define GAMMA_COMMAND_GET_SUPPLY_STATUS		0x0d	/* not implemented */
#define GAMMA_COMMAND_SET_PRESS_UNITS		0x0e
#define GAMMA_COMMAND_GET_PUMP_SIZE		0x11
#define GAMMA_COMMAND_SET_PUMP_SIZE		0x12
#define GAMMA_COMMAND_GET_CAL_FACTOR		0x1d
#define GAMMA_COMMAND_SET_CAL_FACTOR		0x1e
#define GAMMA_COMMAND_SET_AUTO_RESTART		0x33
#define GAMMA_COMMAND_GET_AUTO_RESTART		0x34
#define GAMMA_COMMAND_START_PUMP		0x37
#define GAMMA_COMMAND_STOP_PUMP			0x38
#define GAMMA_COMMAND_GET_SETPOINT		0x3c	/* not implemented */
#define GAMMA_COMMAND_SET_SETPOINT		0x3d	/* not implemented */
#define GAMMA_COMMAND_LOCK_KEYPAD		0x44
#define GAMMA_COMMAND_UNLOCK_KEYPAD		0x45
#define GAMMA_COMMAND_GET_ANALOG_MODE		0x50
#define GAMMA_COMMAND_SET_ANALOG_MODE		0x51
#define GAMMA_COMMAND_IS_HIGH_VOLTAGE_ON	0x61
#define GAMMA_COMMAND_SET_SERIAL_ADDRESS	0x62	/* not implemented */
#define GAMMA_COMMAND_SET_HV_AUTORECOVERY	0x68
#define GAMMA_COMMAND_GET_HV_AUTORECOVERY	0x69
#define GAMMA_COMMAND_SET_FIRMWARE_UPDATE	0x8f	/* not implemented */
#define GAMMA_COMMAND_SET_COMM_MODE		0xd3
#define GAMMA_COMMAND_GET_COMM_MODE		0xd4
#define GAMMA_COMMAND_GETSET_SERIAL_COMM	0x46	/* not implemented */
#define GAMMA_COMMAND_GETSET_ETHERNET_IP	0x47	/* not implemented */
#define GAMMA_COMMAND_GETSET_ETHERNET_MASK	0x48	/* not implemented */
#define GAMMA_COMMAND_GETSET_ETHERNET_GTWY	0x49	/* not implemented */
#define GAMMA_COMMAND_GET_ETHERNET_MAC		0x4a	/* not implemented */
#define GAMMA_COMMAND_SET_COMM_INTERFACE	0x4b
#define GAMMA_COMMAND_INITIATE_FEA		0x4c	/* not implemented */
#define GAMMA_COMMAND_GET_FEA_DATA		0x4d	/* not implemented */
#define GAMMA_COMMAND_INITIATE_HIPOT		0x52	/* not implemented */
#define GAMMA_COMMAND_GETSET_HIPOT_TARGET	0x53	/* not implemented */
#define GAMMA_COMMAND_GETSET_FOLDBACK_VOLTS	0x54	/* not implemented */
#define GAMMA_COMMAND_GETSET_FOLDBACK_PRES	0x55	/* not implemented */
#define GAMMA_COMMAND_MAX 0x92

/* Gamma error codes */
#define GAMMA_ERROR_CODE0			-500
#define GAMMA_ERROR_BAD_COMMAND_CODE		GAMMA_ERROR_CODE0 - 1
#define GAMMA_ERROR_UNKNOWN_COMMAND_CODE	GAMMA_ERROR_CODE0 - 2
#define GAMMA_ERROR_BAD_CHECKSUM		GAMMA_ERROR_CODE0 - 3
#define GAMMA_ERROR_TIMEOUT			GAMMA_ERROR_CODE0 - 4
#define GAMMA_ERROR_UNKNOWN_ERROR		GAMMA_ERROR_CODE0 - 6
#define GAMMA_ERROR_COMM_ERROR			GAMMA_ERROR_CODE0 - 7
#define GAMMA_ERROR_OPEN_PORT			GAMMA_ERROR_CODE0 - 10
#define GAMMA_ERROR_CLOSE_PORT			GAMMA_ERROR_CODE0 - 11
#define GAMMA_ERROR_CONFIG_PORT			GAMMA_ERROR_CODE0 - 12
#define GAMMA_ERROR_WRITE_COMMAND		GAMMA_ERROR_CODE0 - 13
#define GAMMA_ERROR_READ_COMMAND		GAMMA_ERROR_CODE0 - 14
#define GAMMA_ERROR_INVALID_RESPONSE		GAMMA_ERROR_CODE0 - 15
#define GAMMA_ERROR_BAD_RESPONSE_CHECKSUM	GAMMA_ERROR_CODE0 - 16
#define GAMMA_ERROR_VALUE_OUT_OF_RANGE		GAMMA_ERROR_CODE0 - 17

#define GAMMA_ERROR_MAX 18

/* Gamma display codes */
#define GAMMA_DISPLAY_CODE0			-400
#define GAMMA_DISPLAY_COOLDOWN_CYCLES		GAMMA_DISPLAY_CODE0 - 1
#define GAMMA_DISPLAY_VACUUM_LOSS		GAMMA_DISPLAY_CODE0 - 2
#define GAMMA_DISPLAY_SHORT_CIRCUIT		GAMMA_DISPLAY_CODE0 - 3
#define GAMMA_DISPLAY_EXCESS_PRESSURE		GAMMA_DISPLAY_CODE0 - 4
#define GAMMA_DISPLAY_PUMP_OVERLOAD		GAMMA_DISPLAY_CODE0 - 5
#define GAMMA_DISPLAY_SUPPLY_POWER		GAMMA_DISPLAY_CODE0 - 6
#define GAMMA_DISPLAY_START_UNDER_VOLTAGE	GAMMA_DISPLAY_CODE0 - 7
#define GAMMA_DISPLAY_PUMP_IS_ARCING		GAMMA_DISPLAY_CODE0 - 10
#define GAMMA_DISPLAY_THERMAL_RUNAWAY		GAMMA_DISPLAY_CODE0 - 12
#define GAMMA_DISPLAY_UNKNOWN_ERROR		GAMMA_DISPLAY_CODE0 - 19
#define GAMMA_DISPLAY_SAFE_CONN_INTERLOCK	GAMMA_DISPLAY_CODE0 - 20
#define GAMMA_DISPLAY_HVE_INTERLOCK		GAMMA_DISPLAY_CODE0 - 21
#define GAMMA_DISPLAY_SET_PUMP_SIZE		GAMMA_DISPLAY_CODE0 - 22
#define GAMMA_DISPLAY_CALIBRATION_NEEDED	GAMMA_DISPLAY_CODE0 - 23
#define GAMMA_DISPLAY_RESET_REQUIRED		GAMMA_DISPLAY_CODE0 - 24
#define GAMMA_DISPLAY_TEMPERATURE_WARNING	GAMMA_DISPLAY_CODE0 - 25
#define GAMMA_DISPLAY_SUPPLY_OVERHEAT		GAMMA_DISPLAY_CODE0 - 26
#define GAMMA_DISPLAY_CURRENT_LIMITED		GAMMA_DISPLAY_CODE0 - 27
#define GAMMA_DISPLAY_INTERNAL_BUS_ERROR	GAMMA_DISPLAY_CODE0 - 30
#define GAMMA_DISPLAY_HV_CONTROL_ERROR		GAMMA_DISPLAY_CODE0 - 31
#define GAMMA_DISPLAY_CURRENT_CONTROL_ERROR	GAMMA_DISPLAY_CODE0 - 32
#define GAMMA_DISPLAY_CURRENT_MEASURE_ERROR	GAMMA_DISPLAY_CODE0 - 33
#define GAMMA_DISPLAY_VOLTAGE_CONTROL_ERROR	GAMMA_DISPLAY_CODE0 - 34
#define GAMMA_DISPLAY_VOLTAGE_MEASURE_ERROR	GAMMA_DISPLAY_CODE0 - 35
#define GAMMA_DISPLAY_POLARITY_MISMATCH		GAMMA_DISPLAY_CODE0 - 36
#define GAMMA_DISPLAY_HV_NOT_INSTALLED		GAMMA_DISPLAY_CODE0 - 37
#define GAMMA_DISPLAY_INPUT_VOLTAGE_ERROR	GAMMA_DISPLAY_CODE0 - 38

#define GAMMA_DISPLAY_MAX 48

/* Gamma data response length */
#define GAMMA_PRESSURE_DATA_SIZE		13
#define GAMMA_RESPONSE_DATA_SIZE		13

#ifdef CREATOR
char *GammaErrMsg[] = {
  NULL,
  "GAMMA Error (01): Command code/format is not correct, semantics is wrong.",
  "GAMMA Error (02): Command code not recognized, does not exist.",
  "GAMMA Error (03): Bad checksum.",
  "GAMMA Error (04): Command timeout.",
  NULL,
  "GAMMA Error (06): Firmware encountered an unknown error.",
  "GAMMA Error (07): Communication error, zero characters recieved.",
  NULL,
  NULL,
  "GAMMA Error (10): Socket port open error.",
  "GAMMA Error (11): Socket port close error.",
  "GAMMA Error (12): Socket port configuration error.",
  "GAMMA Error (13): Socket port write error.",
  "GAMMA Error (14): Socket port read error.",
  "GAMMA Error (15): Invalid response.",
  "GAMMA Error (16): Bad response checksum.",
  "GAMMA Error (17): Value out of range.",
NULL
};
#else
extern char *GammaErrMsg[];
#endif

#ifdef CREATOR
char *GammaDspMsg[] = {
  NULL,
  "GAMMA Error (01): Too many cooldown cycles (>3) occured during pump starting.",
  "GAMMA Error (02): The voltage dropped below 1200V while pump was running.",
  "GAMMA Error (03): Short circuit condition has been detected during pump starting.",
  "GAMMA Error (04): Excessive pressure condition detected.  Pressure greater than 1.0e-4 Torr detected.",
  "GAMMA Error (05): Too much power delivered to the pump for the given pump size.",
  "GAMMA Error (06): Supply output power detected greater than 50W.",
  "GAMMA Error (07): The voltage did not reach 2000V within the maximum pump starting time of 5 minutes.",
  NULL,
  NULL,
  "GAMMA Error (10): Arcing detected.",
  NULL,
  "GAMMA Error (12): Significant drop in voltage detected during pump starting.",
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  "GAMMA Error (19): Unknown Error.",
  "GAMMA Error (20): Safety interlock connection is not detected.  Check safe-conn connection.",
  "GAMMA Error (21): HVE interlock set or HVE Signal off.",
  "GAMMA Error (22): Pump size is not set.",
  "GAMMA Error (23): Supply calibration has not been performed.  Required for accurate current/pressure readings.",
  "GAMMA Error (24): Supply calibration parameters are outside normal ranges.  System reset will clear all paramters to factory defaults.",
  "GAMMA Error (25): Supply internal temperature is past the threshold.",
  "GAMMA Error (26): Supply internal temperature too high. HV operation is disabled.",
  "GAMMA Error (27): Supply current is limited.  The limit is set by programming the pump size or manually by the user.",
  NULL,
  NULL,
  "GAMMA Error (30): Internal data bus error detected.",
  "GAMMA Error (31): Supply HV control mechanism malfunctioning.  On/Off state is malfunctioning.",
  "GAMMA Error (32): Supply current control mechanism malfunctioning.",
  "GAMMA Error (33): Supply current measuring mechanism malfunctioning.",
  "GAMMA Error (34): Supply HV control mechanism malfunctioning.  Voltage output level is malfunctioning.",
  "GAMMA Error (35): Supply voltage measuring mechanism malfunctioning.",
  "GAMMA Error (36): Internal boards polarity mismatch.",
  "GAMMA Error (37): HV module missing.",
  "GAMMA Error (38): Input power voltage outside 22-26VDC range.  HV operation disabled.",
  NULL,
  "GAMMA Error (40): Socket port open error.",
  "GAMMA Error (41): Socket port close error.",
  "GAMMA Error (42): Socket port configuration error.",
  "GAMMA Error (43): Socket port write error.",
  "GAMMA Error (44): Socket port read error.",
NULL
};
#else
extern char *GammaDspMsg[];
#endif

/* function prototypes */
int gamma_read_version(char *port, char *version);
int gamma_reset(char *port);
int gamma_set_arc_detect(char *port, int yesno);
int gamma_get_arc_detect(char *port, int *yesno);
int gamma_read_current(char *port, float *outcurrent);
int gamma_read_pressure(char *port, float *outpressure); 
int gamma_read_voltage(char *port, int *outvoltage);
int gamma_set_units(char *port, int units);
int gamma_get_pump_size(char *port, int *outsize);
int gamma_set_pump_size(char *port, int size);
int gamma_get_cal_factor(char *port, float *outcalfact);
int gamma_set_cal_factor(char *port, float calfact);
int gamma_set_auto_restart(char *port, int yesno);
int gamma_get_auto_restart(char *port, int *yesno);
int gamma_pump_start(char *port);
int gamma_pump_stop(char *port);
int gamma_lock_keypad(char *port, int lock);
int gamma_get_analog_mode(char *port, int *outmode);
int gamma_set_analog_mode(char *port, int mode);
int gamma_high_voltage_on(char *port, int *yesno);
int gamma_set_hv_autorecovery(char *port, int mode);
int gamma_get_hv_autorecovery(char *port, int *outmode);
int gamma_set_comm_mode(char *port, int mode);
int gamma_get_comm_mode(char *port, int *outmode);
int gamma_set_comm_interface(char *port, int interface);
int gamma_send_command(char *port, char *cmd);
int gamma_send_request(char *port, char *cmd, char *response);
int gamma_create_command_string(char *outstring, int bus_address, 
				int command_code, char *command_data,
				int do_checksum);
int gamma_validate_response(char *response, int command_code);
float getFloatFromGammaResponse(char *response);
int getStringFromGammaResponse(char *response, char *outstring);
float getIntFromGammaResponse(char *response);

#endif  /* _KPRS_GAMMA_H */
