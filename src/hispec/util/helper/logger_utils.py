"""Set up logging helper module."""
import logging
import sys


def setup_logger(name: str, log_file: str = None, level=logging.DEBUG,
                 quiet: bool = False) -> logging.Logger:
    """Setup logger with given name."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers (important for reimporting)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s--%(name)s--%(levelname)s--%(message)s"
    )

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Console handler (unless quiet)
    if not quiet:
        console_formatter = logging.Formatter("%(asctime)s--%(message)s")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
