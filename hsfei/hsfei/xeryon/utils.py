import time
import sys
import logging
from .config import OUTPUT_TO_CONSOLE


def get_actual_time():
    """
    :return: Returns the actual time in ms.
    """
    return int(round(time.time() * 1000))


def get_dpos_epos_string(DPOS, EPOS, Unit):
    """
    :return: A string containting the EPOS & DPOS value's and the current units.
    """
    return str("DPOS: " + str(DPOS) + " " + str(Unit) + " and EPOS: " + str(EPOS) + " " + str(Unit))


def setup_logger(name, level=logging.INFO):
    """
    Sets up a logger with basic console output for info and error messages.

    Args:
        name (str): The name of the logger.
        level: Minimum level for messages to be logged
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # Ensure it resets in tests

    # Handler for stdout (INFO, DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
    stdout_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))

    # Handler for stderr (WARNING, ERROR, CRITICAL)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger


def output_console_factory():
    """Factory function to create a closure for output_console with access to the logger."""
    _logger = None

    def output_console(message, error=False):
        """Logs a message to the console using the provided logger."""
        nonlocal _logger
        if _logger is None:
            _logger = setup_logger("default")
        if error:
            _logger.error(message)
        else:
            _logger.info(message)

    return output_console


# Create instance of the output_console function
output_console = output_console_factory()
