from enum import Enum

class Units(Enum):
    """
    This class is only made for making the program more readable.
    """
    mm = (0, "mm")
    mu = (1, "mu")
    nm = (2, "nm")
    inch = (3, "inches")
    minch = (4, "milli inches")
    enc = (5, "encoder units")
    rad = (6, "radians")
    mrad = (7, "mrad")
    deg = (8, "degrees")

    def __init__(self, ID, str_name):
        self.ID = ID
        self.str_name = str_name

    def __str__(self):
        return self.str_name

    def get_unit(self, str):
        for unit in Units:
            if unit.str_name in str:
                return unit
        return None