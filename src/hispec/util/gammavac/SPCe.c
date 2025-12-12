/*+***************************************************************************
                                                                       
 *  File:     SPCe.c
                                                                        
 *  Purpose:  The functions herein are specific to the Lesker 
              SPCe Gauge SPCe Controller (PGC).

 *  Modification history:
 *    2011/12/02 Stephen Kaye - Initial
 *    2025/07/25 Don Neill - Modify for COO Utils
 *                             
 *-**************************************************************************/
static char sccsid[] = "%W% %E% %U%";

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <math.h>
#include <pthread.h>
#include <termios.h>
#include <errno.h>

#include <errlog.h>

#include "SPCe.h"
#include "kprs.h"

/*
 * Global variables
 */

extern int Simulate;

pthread_mutex_t socket_mutex = PTHREAD_MUTEX_INITIALIZER;

int bus_address=SPCE_BUS_ADDRESS;	/* bus address, 1 for RS-232	*/

/*************************************************************************
 *+
 * Function name: spce_read_version

 * Description: Reads the software version and prints it to the log

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: Returns SPCe error code.
     char *version

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_read_version(char *port, char *version) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_READ_VERSION, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response, 
			SPCE_COMMAND_READ_VERSION)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting version string from response.", 
			__FILE__, __LINE__);

	/* extract pressure from string */
	if ( (err=getStringFromSpceResponse(response, version)) < 0 )
		return err;

  	log_msg(SINFO, LOGLVL_USER1, "%s %d : SPCe Firmware version: %s", 
			__FILE__, __LINE__, version);

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_read_version */


/*************************************************************************
 *+
 * Function name: spce_reset

 * Description: resets gamma pump

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: Returns SPCe error code.

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_reset(char *port) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_RESET, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_command(port, command)) < 0 )
		return err;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_reset */


/*************************************************************************
 *+
 * Function name: spce_set_arc_detect

 * Description: sets arc detect based on value in YESNO

 * Inputs:
     char *port	-- socket port attached to pump
     int yesno	-- 0 - no, 1 - yes

 * Outputs: Returns SPCe error code.

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_set_arc_detect(char *port, int yesno) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_SET_ARC_DETECT, 
			((yesno == 1) ? "YES" : "NO"), 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_ARC_DETECT)) < 0)
		return err;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_arc_detect */


/*************************************************************************
 *+
 * Function name: spce_get_arc_detect

 * Description: gets arc detect setting, puts it in yesno

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: Returns SPCe error code.
     int *yesno -- 1 = "YES" or 0 = "NO"

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_get_arc_detect(char *port, int *yesno) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char stryesno[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_GET_ARC_DETECT, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_ARC_DETECT)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting arc detect state from response.", 
			__FILE__, __LINE__);

	/* extract pressure from string */
	if ( (err=getStringFromSpceResponse(response, stryesno)) < 0 )
		return err;

	if ( strcmp(stryesno,"YES") == 0 )
		*yesno = 1;
	else	*yesno = 0;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_arc_detect */


/*************************************************************************
 *+
 * Function name: spce_read_current

 * Description: reads the current of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     float *outcurrent  -- variable to hold retrieved current value

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_read_current(char *port, float *outcurrent) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_READ_CURRENT, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_READ_CURRENT)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting current from response.", 
			__FILE__, __LINE__);

	/* extract current from string */
	*outcurrent = getFloatFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_read_current */


/*************************************************************************
 *+
 * Function name: spce_read_pressure

 * Description: reads the pressure of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     float *outpressure  -- variable to hold retrieved pressure value

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_read_pressure(char *port, float *outpressure) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_READ_PRESSURE, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_READ_PRESSURE)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting pressure from response.", 
			__FILE__, __LINE__);

	/* extract pressure from string */
	*outpressure = getFloatFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_read_pressure */


/*************************************************************************
 *+
 * Function name: spce_read_voltage

 * Description: reads the voltage of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     int *outvoltage  -- variable to hold retrieved voltage value

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_read_voltage(char *port, int *outvoltage) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_READ_VOLTAGE, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_READ_VOLTAGE)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting voltage from response.", 
			__FILE__, __LINE__);

	/* extract voltage from string */
	*outvoltage = getIntFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_read_voltage */


/*************************************************************************
 *+
 * Function name: spce_set_units

 * Description: sets pressure units to Torr, Mbar, or Pascals

 * Inputs:
     char *port	-- socket port attached to pump
     char *units-- "Torr", "Mbar", or "Pascals" (only checks first char)

 * Outputs: Returns SPCe error code.

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_set_units(char *port, int units) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char spce_units[2];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* check input units */
	if (units == 'M' || units == 'm') {
		spce_units[0] = SPCE_UNITS_MBAR;
	} else if (units == 'P' || units == 'p') {
		spce_units[0] = SPCE_UNITS_PASCAL;
	} else	spce_units[0] = SPCE_UNITS_TORR;
	spce_units[1] = '\0';

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_SET_PRESS_UNITS, spce_units, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_ARC_DETECT)) < 0)
		return err;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_units */


/*************************************************************************
 *+
 * Function name: spce_get_pump_size

 * Description: reads the pump size in L/s of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     int *outsize  -- variable to hold retrieved pump size value

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_get_pump_size(char *port, int *outsize) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_GET_PUMP_SIZE, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_PUMP_SIZE)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting pump size from response.", 
			__FILE__, __LINE__);

	/* extract pump size from string */
	*outsize = getIntFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_pump_size */


/*************************************************************************
 *+
 * Function name: spce_set_pump_size

 * Description: reads the pump size in L/s of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump
     int size  -- pump size in L/s

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_pump_size(char *port, int size) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strsize[5];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create size string */
	if (size >= 0 && size <= 9999) {
		sprintf(strsize,"%04d",size);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_PUMP_SIZE, strsize, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_PUMP_SIZE)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_pump_size */


/*************************************************************************
 *+
 * Function name: spce_get_cal_factor

 * Description: reads the calibration factor (0-9.99) of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     float *outcalfact  -- variable to hold retrieved calibration factor

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_get_cal_factor(char *port, float *outcalfact) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_GET_CAL_FACTOR, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_CAL_FACTOR)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting cal factor from response.", 
			__FILE__, __LINE__);

	/* extract cal factor from string */
	*outcalfact = getFloatFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_cal_factor */


/*************************************************************************
 *+
 * Function name: spce_set_cal_factor

 * Description: sets the gamma pump calibration factor (0-9.99).

 * Inputs:
     char *port	-- socket port attached to pump
     float calfact  -- calibration factor (0.00 - 9.99)

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_cal_factor(char *port, float calfact) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strcalfact[5];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create size string */
	if (calfact >= 0.00 && calfact <= 9.99) {
		sprintf(strcalfact,"%4.2f",calfact);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_CAL_FACTOR, strcalfact, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_CAL_FACTOR)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_cal_factor */


/*************************************************************************
 *+
 * Function name: spce_set_auto_restart

 * Description: sets auto restart for the gamma pump to yes or no.

 * Inputs:
     char *port	-- socket port attached to pump
     int yesno	-- 0 - no, 1 - yes

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_auto_restart(char *port, int yesno) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char stryesno[4];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create set string */
	if (yesno == 1) {
		sprintf(stryesno,"YES");
	} else {
		sprintf(stryesno,"NO");
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_AUTO_RESTART, stryesno, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_AUTO_RESTART)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_auto_restart */


/*************************************************************************
 *+
 * Function name: spce_get_auto_restart

 * Description: gets the auto restart setting for the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: Returns SPCe error code.
     int *yesno -- 1 = "YES" or 0 = "NO"

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_get_auto_restart(char *port, int *yesno) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char stryesno[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_GET_AUTO_RESTART, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_AUTO_RESTART)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting auto restart state from response.", 
			__FILE__, __LINE__);

	/* extract status from string */
	if ( (err=getStringFromSpceResponse(response, stryesno)) < 0 )
		return err;

	if ( strcmp(stryesno,"YES") == 0 )
		*yesno = 1;
	else	*yesno = 0;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_auto_restart */


/*************************************************************************
 *+
 * Function name: spce_pump_start

 * Description: starts the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_pump_start(char *port) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_START_PUMP, NULL, 1)) < 0 ) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_START_PUMP)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_pump_start */


/*************************************************************************
 *+
 * Function name: spce_pump_stop

 * Description: stops the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_pump_stop(char *port) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_STOP_PUMP, NULL, 1)) < 0 ) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_STOP_PUMP)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_pump_stop */


/*************************************************************************
 *+
 * Function name: spce_lock_keypad

 * Description: Locks/Unlocks the keypad according to value in LOCK

 * Inputs:
     char *port	-- socket port attached to pump
     int lock	-- 0 - unlock, 1 - lock

 * Outputs: Returns SPCe error code.

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_lock_keypad(char *port, int lock) {

	int err=0;
	int command_code = ((lock == 1) ?  SPCE_COMMAND_LOCK_KEYPAD :
		 			   SPCE_COMMAND_UNLOCK_KEYPAD);
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
					command_code, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response, command_code)) < 0)
		return err;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_lock_keypad */


/*************************************************************************
 *+
 * Function name: spce_get_analog_mode

 * Description: reads the analog mode of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     int *outmode  -- variable to hold retrieved analog mode value

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_get_analog_mode(char *port, int *outmode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_GET_ANALOG_MODE, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_ANALOG_MODE)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting analog mode from response.", 
			__FILE__, __LINE__);

	/* extract analog mode from string */
	*outmode = getIntFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_analog_mode */


/*************************************************************************
 *+
 * Function name: spce_set_analog_mode

 * Description: sets the gamma pump analog_mode (0-6,8-10)

 * Inputs:
     char *port	-- socket port attached to pump
     int mode	-- analog mode value (0-6,8-10)

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_analog_mode(char *port, int mode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strmode[3];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create mode string */
	if ( mode >= 0 && mode <= 10 && mode != 7 ) {
		sprintf(strmode,"%d",mode);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_ANALOG_MODE, strmode, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_ANALOG_MODE)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_analog_mode */


/*************************************************************************
 *+
 * Function name: spce_high_voltage_on

 * Description: gets the high voltage setting for the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: Returns SPCe error code.
     int *yesno -- 1 = "YES" or 0 = "NO"

 * Modification History:
      2012/01/10 SK  -- Initial.
      2014/02/04 DN adapted to SPCe controller
 *-
*************************************************************************/
int spce_high_voltage_on(char *port, int *yesno) {

	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char stryesno[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Creating command string.", 
			__FILE__, __LINE__);

	/* create command string */
	if ( (err=spce_create_command_string(command, bus_address, 
			SPCE_COMMAND_IS_HIGH_VOLTAGE_ON, NULL, 1)) < 0) 
		return err;

	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_IS_HIGH_VOLTAGE_ON)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting high voltage state from response.", 
			__FILE__, __LINE__);

	/* extract status from string */
	if ( (err=getStringFromSpceResponse(response, stryesno)) < 0 )
		return err;

	if ( strcmp(stryesno,"YES") == 0 )
		*yesno = 1;
	else	*yesno = 0;

  	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_high_voltage_on */


/*************************************************************************
 *+
 * Function name: spce_set_hv_autorecovery

 * Description: sets the gamma pump HV autorecovery mode (0-2)

 * Inputs:
     char *port	-- socket port attached to pump
     int mode	-- HV autorecovery mode value (0-3):
     			0 - disabled
			1 - enable auto HV start
			2 - enable auto power start (no HV)

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_hv_autorecovery(char *port, int mode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strmode[3];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create mode string */
	if ( mode >= 0 && mode <= 2 ) {
		sprintf(strmode,"%d",mode);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_HV_AUTORECOVERY, strmode, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_HV_AUTORECOVERY)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_hv_autorecovery */


/*************************************************************************
 *+
 * Function name: spce_get_hv_autorecovery

 * Description: reads the HV autorecovery mode of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     int *outmode  -- variable to hold retrieved HV auto recovery mode value
     			(see spce_set_hv_autorecovery)

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_get_hv_autorecovery(char *port, int *outmode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_GET_HV_AUTORECOVERY, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_HV_AUTORECOVERY)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting HV autorecovery mode from response.", 
			__FILE__, __LINE__);

	/* extract HV autorecovery mode from string */
	*outmode = getIntFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_hv_autorecovery */


/*************************************************************************
 *+
 * Function name: spce_set_comm_mode

 * Description: sets the gamma pump comm mode (0-2)

 * Inputs:
     char *port	-- socket port attached to pump
     int mode	-- comm mode value (0-3):
     			0 - Local
			1 - Remote
			2 - Full

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_comm_mode(char *port, int mode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strmode[3];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create mode string */
	if ( mode >= 0 && mode <= 2 ) {
		sprintf(strmode,"%d",mode);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_COMM_MODE, strmode, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_COMM_MODE)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_comm_mode */


/*************************************************************************
 *+
 * Function name: spce_get_comm_mode

 * Description: reads the comm mode of the gamma pump.

 * Inputs:
     char *port	-- socket port attached to pump

 * Outputs: 
     int *outmode  -- variable to hold retrieved commy mode value
     			(see spce_set_comm_mode)

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_get_comm_mode(char *port, int *outmode) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_GET_COMM_MODE, NULL, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_GET_COMM_MODE)) < 0)
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: extracting comm mode from response.", 
			__FILE__, __LINE__);

	/* extract comm mode from string */
	*outmode = getIntFromSpceResponse(response);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_get_comm_mode */


/*************************************************************************
 *+
 * Function name: spce_set_comm_interface

 * Description: sets the gamma pump comm interface (0-2)

 * Inputs:
     char *port	-- socket port attached to pump
     int interface	-- comm interface value (0-3):
     			0 - RS232
			1 - RS422
			2 - RS485
			3 - RS485 (full duplex)
			4 - Ethernet
			5 - USB

 * Outputs: 

 * Returns: 0 or gamma error code.

 * Modification History:
      2011/12/02 SK -- Initial.
      2014/02/04 DN Modified for SPCe controller
 *-
*************************************************************************/
int spce_set_comm_interface(char *port, int interface) {
  
	int err=0;
	char command[MAX_COMMAND_LENGTH];
	char response[MAX_RESPONSE_LENGTH];
	char strinterface[3];

	log_msg(SINFO, LOGLVL_USER3, 
		"%s %d: entering %s", __FILE__, __LINE__, __FUNCTION__);

	log_msg(SDEBUG, LOGLVL_USER4, 
		"%s %d: Creating command string.", __FILE__, __LINE__);

	/* create interface string */
	if ( interface >= 0 && interface <= 5 ) {
		sprintf(strinterface,"%d",interface);
	} else {
		return SPCE_ERROR_VALUE_OUT_OF_RANGE;
	}

	/* generate command string */
	if ( (err=spce_create_command_string(command, bus_address,
			SPCE_COMMAND_SET_COMM_INTERFACE, strinterface, 1)) < 0 ) 
		return err;


	if ( (err=spce_send_request(port, command, response)) < 0 )
		return err;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: checking for errors.", 
			__FILE__, __LINE__);

	/* check for errors */
	if ( (err=spce_validate_response(response,
			SPCE_COMMAND_SET_COMM_INTERFACE)) < 0)
		return err;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_set_comm_interface */


/*************************************************************************
 *+
 * Function name: spce_send_command

 * Description: send a command to the socket port

 * Inputs:
     char *port	-- socket port
     int cmd	-- command code (see kprs_gamma.h)

 * Returns: 0 or gamma error code.

 * Modification History:
      2014/02/04 DN Initial
 *-
*************************************************************************/
int spce_send_command(char *port, char *cmd) {
  
	int err=0;
	int cerr=0;
	int socket_fd;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	if ( !Simulate ) {

		/* lock socket port */
		pthread_mutex_lock(&socket_mutex);

		/* open port */
		log_msg(SINFO, LOGLVL_USER4, 
			"%s %d, %s:  Calling setupSocketInterface",
			__FILE__, __LINE__, __FUNCTION__);
		
		if ( (socket_fd=setupSocketInterface(port, 0)) < 0) {
			pthread_mutex_unlock(&socket_mutex);
			return SPCE_ERROR_OPEN_PORT;
		}
		log_msg(SINFO, LOGLVL_USER4, 
			"%s %d, %s:  setupSocketInterface=%d, success",
			__FILE__, __LINE__, __FUNCTION__, socket_fd);

		/* write command to port */
		log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Writing command.", 
			__FILE__, __LINE__);

		if ( (err=socketport_write(socket_fd, cmd, strlen(cmd))) < 0) {
			if ((cerr = socketport_close(socket_fd)) < 0) {
				err = SPCE_ERROR_CLOSE_PORT;
				errlog(SERROR, "%s %d: %s", __FILE__, __LINE__, 
					SpceErrMsg[SPCE_ERROR_CODE0-err]);
			}
			pthread_mutex_unlock(&socket_mutex);
			return SPCE_ERROR_WRITE_COMMAND;
		}
		log_msg(SINFO, LOGLVL_USER4,
			"%s %d, %s:  socketport_write ret=%d, success",
			__FILE__, __LINE__, __FUNCTION__, err);

		/* close port */
		if ((err=socketport_close(socket_fd)) < 0)
			err=SPCE_ERROR_CLOSE_PORT;

		/* unlock socket port */
		pthread_mutex_unlock(&socket_mutex);

	}	/* end if ( !Simulate ) */

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
		__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_send_command */


/*************************************************************************
 *+
 * Function name: spce_send_request

 * Description: send a command to the socket port and return the response

 * Inputs:
     char *port	-- socket port
     int cmd	-- command code (see kprs_gamma.h)
     char *response	-- response to command

 * Returns: 0 or gamma error code.

 * Modification History:
      2014/02/04 DN Initial
 *-
*************************************************************************/
int spce_send_request(char *port, char *cmd, char *response) {
  
	int err=0;
	int cerr=0;
	int charsread=0;
	int socket_fd;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	if ( !Simulate ) {

		/* lock socket port */
		pthread_mutex_lock(&socket_mutex);

		/* open port */
		log_msg(SINFO, LOGLVL_USER4, 
			"%s %d, %s:  Calling setupSocketInterface",
			__FILE__, __LINE__, __FUNCTION__);
		
		if ( (socket_fd=setupSocketInterface(port, 0)) < 0) {
			pthread_mutex_unlock(&socket_mutex);
			return SPCE_ERROR_OPEN_PORT;
		}
		log_msg(SINFO, LOGLVL_USER4, 
			"%s %d, %s:  setupSocketInterface=%d, success",
			__FILE__, __LINE__, __FUNCTION__, socket_fd);

		/* write command to port */
		log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Writing command.", 
			__FILE__, __LINE__);

		if ( (err=socketport_write(socket_fd, cmd, strlen(cmd))) < 0) {
			if ((cerr = socketport_close(socket_fd)) < 0) {
				err = SPCE_ERROR_CLOSE_PORT;
				errlog(SERROR, "%s %d: %s", __FILE__, __LINE__, 
					SpceErrMsg[SPCE_ERROR_CODE0-err]);
			}
			pthread_mutex_unlock(&socket_mutex);
			return SPCE_ERROR_WRITE_COMMAND;
		}
		log_msg(SINFO, LOGLVL_USER4,
			"%s %d, %s:  socketport_write ret=%d, success",
			__FILE__, __LINE__, __FUNCTION__, err);

		/* wait for response */
		usleep(SPCE_TIME_BETWEEN_COMMANDS);

		/* read response */
		log_msg(SDEBUG, LOGLVL_USER4, "%s %d: Reading response.", 
			__FILE__, __LINE__);

		memset( response, (char)'\0', sizeof(response) );

		if ( (charsread=socketport_read(socket_fd, MAX_RESPONSE_LENGTH, 
			 	response )) < 0) {
			if ((cerr = socketport_close(socket_fd)) < 0) {
				err = SPCE_ERROR_CLOSE_PORT;
				errlog(SERROR, "%s %d: %s", __FILE__, __LINE__, 
					SpceErrMsg[SPCE_ERROR_CODE0-err]);
			}
			pthread_mutex_unlock(&socket_mutex);
			return SPCE_ERROR_READ_COMMAND;
		}
		log_msg(SINFO, LOGLVL_USER4,
			"%s %d, %s:  socketport_read ret=%d, success",
			__FILE__, __LINE__, __FUNCTION__, charsread );

		/* close port */
		if ((err=socketport_close(socket_fd)) < 0)
			err=SPCE_ERROR_CLOSE_PORT;

		/* unlock socket port */
		pthread_mutex_unlock(&socket_mutex);

		/* remove all non-printable chars from response? */

	}	/* end if ( !Simulate ) */

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
		__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_send_request */


/*************************************************************************
 *+
 * Function name: spce_create_command_string

 * Description: creates the proper command string to be sent to the gamma
                pump based on the input variables.

 * Inputs:
     char *outstring       --  string to receive command           
     int   bus_address     --  bus address (1 = RS232)
     int   command_code    --  gamma mgc command code
     int   nchar	   --  number of characters in command_code (2 or 3)
     int   val		   --  parameter int value, if necessary
     float fval		   --  parameter float value, if necessary

 * Outputs: Returns length of command or SPCe error code if there is an error.

 * Modification History:
      2011/12/02 SK  -- Initial.
      2014/02/03 DN  Modified for GAMMA
 *-
*************************************************************************/
int spce_create_command_string(
   char *outstring,	/* string to receive command	*/
   int bus_address,	/* bus address (1 = RS232)	*/
   int command_code,	/* gamma command code		*/ 
   char *command_data,	/* data for command or NULL	*/
   int do_checksum	/* 0 - no, other - yes		*/
   ) 
{

  /* 
   *  This function creates a command string to be passed to 
   *  the SPCe vacuum controller.
   *  See SPCe vacuum SPCe controller user manual
   *  from gammavacuum.com for details
   *
   *  commands use this format:
   *    {attention char} {bus_address} {command code} {data} {termination}
   *          ~              ba              cc         data       \r
   *
   *    with 
   *    ba   = address value between 01 and FF.
   *    cc   = character string representing command (2 bytes)
   *	data = optional value for command (e.g. baud rate, adress setting, etc.)
   *
   */

	char out_command[MAX_COMMAND_LENGTH];
	char temp_command[MAX_COMMAND_LENGTH];
	char temp_code[MAX_CODE_LENGTH];
	char *p;
  	int err=0;
	int cksm=0;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);
  	log_msg(SDEBUG, LOGLVL_USER4, 
			"%s %d: Creating command string for SPCe pump.", 
			__FILE__, __LINE__);
	
	/* create command code string */
	sprintf(temp_code, "%.2X", command_code);

	/* determine which command was called, and then construct
	command based on parameters if err == 0 */
	if (err == 0) {
		switch (command_code) {
			/* just the command code */
			case SPCE_COMMAND_READ_MODEL:
			case SPCE_COMMAND_READ_VERSION:
			case SPCE_COMMAND_RESET:
			case SPCE_COMMAND_GET_ARC_DETECT:
			case SPCE_COMMAND_READ_CURRENT:
			case SPCE_COMMAND_READ_PRESSURE:
			case SPCE_COMMAND_READ_VOLTAGE:
			case SPCE_COMMAND_GET_SUPPLY_STATUS:
			case SPCE_COMMAND_GET_PUMP_SIZE:
			case SPCE_COMMAND_GET_CAL_FACTOR:
			case SPCE_COMMAND_GET_AUTO_RESTART:
			case SPCE_COMMAND_START_PUMP:
			case SPCE_COMMAND_STOP_PUMP:
			case SPCE_COMMAND_GET_SETPOINT:
			case SPCE_COMMAND_LOCK_KEYPAD:
			case SPCE_COMMAND_UNLOCK_KEYPAD:
			case SPCE_COMMAND_GET_ANALOG_MODE:
			case SPCE_COMMAND_IS_HIGH_VOLTAGE_ON:
			case SPCE_COMMAND_GET_HV_AUTORECOVERY:
			case SPCE_COMMAND_SET_FIRMWARE_UPDATE:
			case SPCE_COMMAND_GET_COMM_MODE:
			case SPCE_COMMAND_GET_ETHERNET_MAC:
			case SPCE_COMMAND_INITIATE_FEA:
			case SPCE_COMMAND_INITIATE_HIPOT:
				/* need trailing space for checksum */
				sprintf(temp_command, " %.2X %s ", 
						bus_address, temp_code);
				break;

			/* GET/SET command codes */
			case SPCE_COMMAND_GETSET_SERIAL_COMM:
			case SPCE_COMMAND_GETSET_ETHERNET_IP:
			case SPCE_COMMAND_GETSET_ETHERNET_MASK:
			case SPCE_COMMAND_GETSET_ETHERNET_GTWY:
			case SPCE_COMMAND_GETSET_HIPOT_TARGET:
			case SPCE_COMMAND_GETSET_FOLDBACK_VOLTS:
			case SPCE_COMMAND_GETSET_FOLDBACK_PRES:
				/* need trailing space for checksum */
				if (command_data == NULL) {
					sprintf(temp_command, " %.2X %s ", 
						bus_address, temp_code);
				} else {
					sprintf(temp_command, " %.2X %s %s ", 
						bus_address, temp_code,
						command_data);
				}
				break;

			/* command plus data */
			case SPCE_COMMAND_SET_ARC_DETECT:
			case SPCE_COMMAND_SET_PRESS_UNITS:
			case SPCE_COMMAND_SET_PUMP_SIZE:
			case SPCE_COMMAND_SET_CAL_FACTOR:
			case SPCE_COMMAND_SET_AUTO_RESTART:
			case SPCE_COMMAND_SET_SETPOINT:
			case SPCE_COMMAND_SET_ANALOG_MODE:
			case SPCE_COMMAND_SET_SERIAL_ADDRESS:
			case SPCE_COMMAND_SET_HV_AUTORECOVERY:
			case SPCE_COMMAND_SET_COMM_MODE:
			case SPCE_COMMAND_SET_COMM_INTERFACE:
			case SPCE_COMMAND_GET_FEA_DATA:
				/* need trailing space for checksum */
				sprintf(temp_command, " %.2X %s %s ", 
					bus_address, temp_code, command_data);
				break;

			/* invalid command */
			default:
				err = SPCE_ERROR_BAD_COMMAND_CODE;

		}	/* end switch(command_code) */

		/* make sure we still have a valid command */
		if (err == 0) {

			/* do we need the checksum? */
			if (do_checksum != 0) {
				p = temp_command;
				while (*p) cksm = cksm + (int)(*p++);
				cksm = cksm % 256;
			}

			/* final output command */
			sprintf(out_command, "~%s%.2X\r", temp_command, cksm);

			/* set err to length of command */
			err = strlen(out_command);

  			/* copy the new command string from temp 
		 	* string into output string */
			strcpy(outstring, out_command);
		}
	}	/* end if (err == 0) */

	log_msg(SINFO, LOGLVL_USER4, "%s %d: command string = {%s}", 
			__FILE__, __LINE__, outstring);

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: spce_create_command_string */


/*************************************************************************
 *+
 * Function name: spce_validate_response

 * Description: Processes response read from serial port to determine
                if there was an error.

 * Inputs: 
     char *response   -- string received from controller, read from serialport
     int  command_code -- command code of command that generated response

 * Outputs: Returns SPCe error code.

 * Modification History:
      2002/12/17 JLW -- Initial.
      2006/06/27 CRO -- Superficial mods for MOSFIRE.
      2014/02/06 JDN -- Major re-write for GAMMA
 *-
*************************************************************************/
int spce_validate_response(char *response, int command_code) {

	const char del[2] = " ";
	int err=0;
	char *substr, *p;
	int bus, i, offset, rcksm, cksm=0;

	log_msg(SINFO, LOGLVL_USER3, "%s %d: entering %s", 
			__FILE__, __LINE__, __FUNCTION__);

	/* all responses must start with the bus address */
	bus = atoi(response);
	if (bus != bus_address) {

		/* bad response string */
		err = SPCE_ERROR_INVALID_RESPONSE;

	/* bus address OK */
	} else {

		/* now get status mnemonic */
		substr = response + 3*sizeof(char);

		/* check for error condition */
		if ( strncmp(substr,"ER",2) == 0 ) {

			/* get error code */
			substr += 3*sizeof(char);
			err = SPCE_ERROR_CODE0 - atoi(substr);

		/* status OK */
		} else {

			/* offset to beginning of checksum in response */
			offset = strlen(response) - 3*sizeof(char);

			/* extract response checksum (Hex) */
			rcksm = strtol(response+offset,NULL,16);

			/* calculate response checksum */
			p = response;
			for ( i=0 ; i<=offset-1 ; i++ )
				cksm = cksm + *p++;
			cksm = cksm % 256;

			/* make sure they match */
			if (rcksm != cksm)
				err = SPCE_ERROR_BAD_RESPONSE_CHECKSUM;

		}	/* status OK */

	}	/* bus address OK */


	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;

}	/* end * Function name: spce_validate_response */

/*************************************************************************
 *+
 * Function name: getFloatFromSpceResponse

 * Description: Convert response to floating-point number.

 * Inputs: 
     char *spce_response   -- string read from serialport

 * Outputs: Returns float value or -1. for bad response

 * Modification History:
      2012/12/17 SK -- Initial.
      2014/02/06 DN -- Added more error checking.
 *-
*************************************************************************/
float getFloatFromSpceResponse(char *response) {
	char	*substr;
	float num;
	int fstat;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: entering %s.", 
			__FILE__, __LINE__, __FUNCTION__);

	/* offset to beginning of data */
	substr = strstr(response, "OK") + 6*sizeof(char);

	fstat = sscanf(substr,"%g", &num);

	if (fstat != 1) {
		num = -1.;
		errlog(SERROR, "%s %d (%s): Invalid float value", 
			__FILE__, __LINE__, __FUNCTION__);
	} else {

		log_msg(SDEBUG, LOGLVL_USER4, "%s %d: %s, value = %e", 
			__FILE__, __LINE__, __FUNCTION__, num);
	}

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return num;
}	/* end * Function name: getFloatFromSpceResponse */


/*************************************************************************
 *+
 * Function name: getStringFromSpceResponse

 * Description: Convert response to string.

 * Inputs: 
     char *spce_response   -- string read from serialport

 * Outputs: Returns SPCe error code.
     char *outstring        -- data string from response

 * Modification History:
      2014/02/27 DN -- Initial.
 *-
*************************************************************************/
int getStringFromSpceResponse(char *response, char *outstring) {
	char	*substr;
	int data_size;
	int err=0;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: entering %s.", 
			__FILE__, __LINE__, __FUNCTION__);

	/* validate OK response */
	if ( (substr=strstr(response, "OK")) == NULL ) {

		err = SPCE_ERROR_INVALID_RESPONSE;
		errlog(SERROR, "%s %d (%s): Invalid string", 
			__FILE__, __LINE__, __FUNCTION__);

	/* response OK */
	} else {

		/* offset from "OK" to beginning of data */
		substr += 6*sizeof(char);

		/* find size of data */
		data_size = strlen(substr) - 4*sizeof(char);

		/* verify the size of the data string */
		if (data_size <= 0 || data_size >= MAX_RESPONSE_LENGTH) {

			err = SPCE_ERROR_INVALID_RESPONSE;
			errlog(SERROR, "%s %d (%s): Invalid string", 
				__FILE__, __LINE__, __FUNCTION__);

		/* data string size OK */
		} else {

			strncpy(outstring, substr, data_size);
			outstring[data_size] = '\0';	/* null terminate */
			log_msg(SDEBUG, LOGLVL_USER4, "%s %d: %s, string = %s", 
				__FILE__, __LINE__, __FUNCTION__, outstring);
		}

	}	/* response OK */

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return err;
}	/* end * Function name: getStringFromSpceResponse */


/*************************************************************************
 *+
 * Function name: getIntFromSpceResponse

 * Description: Convert response to floating-point number.

 * Inputs: 
     char *spce_response   -- string read from serialport

 * Outputs: integer value or -1 for bad response

 * Modification History:
      2012/12/17 SK -- Initial.
      2014/02/06 DN -- Added more error checking.
 *-
*************************************************************************/
float getIntFromSpceResponse(char *response) {
	char	*substr;
	int num;
	int fstat;

	log_msg(SDEBUG, LOGLVL_USER4, "%s %d: entering %s.", 
			__FILE__, __LINE__, __FUNCTION__);

	/* offset to beginning of data */
	substr = strstr(response, "OK") + 6*sizeof(char);

	fstat = sscanf(substr,"%d", &num);

	if (fstat != 1) {
		num = -1;
		errlog(SERROR, "%s %d (%s): Invalid int value", 
			__FILE__, __LINE__, __FUNCTION__);
	} else {

		log_msg(SDEBUG, LOGLVL_USER4, "%s %d: %s, value = %d", 
			__FILE__, __LINE__, __FUNCTION__, num);
	}

	log_msg(SINFO, LOGLVL_USER3, "%s %d: exiting %s", 
			__FILE__, __LINE__, __FUNCTION__);

	return num;
}	/* end * Function name: getIntFromSpceResponse */

