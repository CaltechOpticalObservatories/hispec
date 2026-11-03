"""Shared base class for the hardware device driver daemons.

Methods common to all hardware device driver daemons.
"""
from hispec.daemon import HispecDaemon  # pylint: disable=E0611

class HispecDriverDaemon(HispecDaemon):  # pylint: disable=W0223,too-many-public-methods
    """Base class for a daemon that controls hardware through a device driver (controller)

    Device drivers are submodules in src/hispec/driver that all inherit these functions from
    hardware_device_base.py:

    is_connected
    get_status
    """

    def __init__(self, controller=None) -> None:
        """Initialize the hardware driver daemon.

        libby's from_config() builds the daemon with no arguments, so a
        subclass either passes its driver here or calls this first and then
        sets self.controller. Connect the driver later, once config is loaded.
        """
        super().__init__()
        self.controller = controller

    def _connected(self) -> bool:
        """True when the driver holds an open session to the controller."""
        return self.controller is not None and bool(self.controller.is_connected())

    def _status(self):
        """Return the status of the driver."""
        if not self._connected():
            return str((-1, "ERROR: Not connected to hardware"))
        return str(self.controller.get_status())

    def _shutdown(self):
        """Shutdown the daemon"""
        self.logger.info("Shutting down")
        self.controller.disconnect()
        self.request_stop()
