import time
from .config import OUTPUT_TO_CONSOLE

def getActualTime():
    """
    :return: Returns the actual time in ms.
    """
    return int(round(time.time() * 1000))


def getDposEposString(DPOS, EPOS, Unit):
    """
    :return: A string containting the EPOS & DPOS value's and the current units.
    """
    return str("DPOS: " + str(DPOS) + " " + str(Unit) + " and EPOS: " + str(EPOS) + " " + str(Unit))


def outputConsole(message, error=False, force=True):
    if OUTPUT_TO_CONSOLE is True:
        if error is True:
            print("\033[91m" + "ERROR: " + message + "\033[0m")
        else:
            print(message)

