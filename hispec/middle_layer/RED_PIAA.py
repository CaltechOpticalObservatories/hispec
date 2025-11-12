# standard library
from time import time, sleep
from abc import ABC, abstractmethod
from configparser import ConfigParser
import threading, os, traceback, logging

class Device_cmds:
    """Class for controlling a generic Device through shared memory

    method list:
    Queries:
        is_active
        is_connected
        is_closed_loop
        is_referenced
        is_moving
        get_error
        get_pos
        get_named_pos
        get_target
    Commands
        connect
        disconnect
        home
        close_loop
        reference
        set_pos
        activate_control_script
        kill_control_script
        load_presets