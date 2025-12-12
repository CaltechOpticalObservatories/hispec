"""Script for logging to InfluxDB."""
import time
import sys
import json
import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from urllib3.exceptions import ReadTimeoutError
import onewire


def main(config_file):
    """Query user for setup info and start logging to InfluxDB."""
    # pylint: disable=too-many-statements,too-many-locals

    # read the config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    # set up logging
    logfile = cfg['logfile']
    if logfile is None:
        logfile = __name__.rsplit('.', 1)[-1]
    logger = logging.getLogger(logfile)
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    # log to console by default
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    # Do we have a logfile?
    if cfg['logfile'] is not None:
        # log to a file
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s() - %(message)s')
        file_handler = logging.FileHandler(logfile if ".log" in logfile else logfile + '.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # get channels to log
    channels = cfg['log_channels']
    locations = cfg['log_locations']

    # Try/except to catch exceptions
    db_client = None
    try:
        # Loop until ctrl-C
        while True:
            try:
                # Connect to onewire
                ow = onewire.ONEWIRE()
                logger.info('Connecting to OneWire controller...')
                ow.connect(cfg['device_host'], cfg['device_port'])
                ow.get_data()
                ow_data = ow.ow_data.read_sensors()

                # Connect to InfluxDB
                logger.info('Connecting to InfluxDB...')
                db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                                           org=cfg['db_org'])
                write_api = db_client.write_api(write_options=SYNCHRONOUS)

                for sens_no, sensor in enumerate(ow_data):
                    location = locations[str(sens_no+1)]
                    for chan in channels:
                        value = sensor[chan]
                        point = (
                            Point("onewire")
                            .field(channels[chan]['field']+str(sens_no+1), value)
                            .tag("location", location)
                            .tag("units", channels[chan]['units'])
                            .tag("channel", f"{cfg['db_channel']}")
                        )
                        write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=point)
                        logger.debug(point)

                # Close db connection
                logger.info('Closing connection to InfluxDB...')
                db_client.close()
                db_client = None

            # Handle exceptions
            except ReadTimeoutError as e:
                logger.critical("ReadTimeoutError: %s, will retry.", e)
            except Exception as e:
                logger.critical("Unexpected error: %s, will retry.", e)

            # Sleep for interval_secs
            logger.info("Waiting %d seconds...", cfg['interval_secs'])
            time.sleep(cfg['interval_secs'])

    except KeyboardInterrupt:
        logger.critical("Shutting down InfluxDB logging...")
        if db_client:
            db_client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
