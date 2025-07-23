"""
Interface for Inficon VGC502 pressure gauge using TCP/IP.
"""

import asyncio
import sys
from hispec.util.helper import logger_utils


class InficonVGC502:
    def __init__(self, address: str, port: int, *,
                timeout: int = 1, log: bool = True, quiet: bool = False) -> None:
        """
        Initialize the InficonVGC502 interface.

        Args:
            address (str): IP address of the device.
            port (int): TCP port to connect to.
            timeout (int, optional): Connection timeout. Defaults to 1.
            log (bool, optional): Enable logging. Defaults to True.
            quiet (bool, optional): Quiet mode for logger. Defaults to False.
        """
        self.address = address
        self.port = int(port)
        self.timeout = timeout
        self.reader = None
        self.writer = None

        # Initialize logger
        self.logger = logger_utils.setup_logger(
            __name__, "InficonVGC502.log", quiet=quiet
        ) if log else None

        if self.logger:
            self.logger.info("Logger initialized for InficonVGC502")

    async def __aenter__(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.address, self.port)
            if self.logger:
                self.logger.info("Connected to %s:%s", self.address, self.port)
        except ConnectionRefusedError as err:
            if self.logger:
                self.logger.error("Connection refused: %s", err)
            raise DeviceConnectionError(f"Could not connect to {self.address}:{self.port}") from err
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            if self.logger:
                self.logger.info("Connection closed")

    async def read_pressure(self, gauge=1):
        """
        Read pressure from specified gauge.

        Args:
            gauge (int): Gauge number to query.

        Returns:
            float: Pressure value or sys.float_info.max on failure.
        """
        command = f'PR{gauge}\r\n'.encode('ascii')
        if self.logger:
            self.logger.debug("Sending command: %s", command)
        self.writer.write(command)
        await self.writer.drain()

        try:
            acknowledgment = await self.reader.readuntil(b'\r\n')
            acknowledgment = acknowledgment.strip()
            if self.logger:
                self.logger.debug("Acknowledgment received: %s", acknowledgment)
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.warning("Timeout waiting for acknowledgment")
            return sys.float_info.max

        if acknowledgment == b'\x06':
            if self.logger:
                self.logger.debug("ACK received, sending ENQ")
            self.writer.write(b'\x05')
            await self.writer.drain()
            try:
                response = await self.reader.readuntil(b'\r\n')
                response_str = response.strip().decode('ascii')
                if self.logger:
                    self.logger.debug("Pressure response: %s", response_str)
                return float(response_str.split(',')[1])
            except (IndexError, ValueError) as e:
                if self.logger:
                    self.logger.error("Failed to parse response: %s", e)
                return sys.float_info.max

        if acknowledgment == b'\x15':
            if self.logger:
                self.logger.error("Received NAK: Wrong command")
            raise WrongCommandError("Wrong command sent.")

        if self.logger:
            self.logger.error("Unknown acknowledgment: %s", acknowledgment)
        raise UnknownResponse(f"Unknown response: {acknowledgment}")

    async def set_pressure_unit(self, unit: int):
        """
        Set the pressure unit.

        unit:
            0 –> mbar/bar
            1 –> Torr
            2 –> Pascal
            3 –> Micron
            4 –> hPascal (default)
            5 –> Volt
        """
        if unit not in range(0, 6):
            raise ValueError(f"Invalid unit: {unit}. Must be between 0 and 5.")

        command = f'UNI,{unit}\r\n'.encode('ascii')
        if self.logger:
            self.logger.debug("Sending command to set unit: %s", command)
        self.writer.write(command)
        await self.writer.drain()

        response = await self.reader.readuntil(b'\r\n')
        response = response.strip()
        if self.logger:
            self.logger.debug("Response to set unit: %s", response)

        if response == b'\x06':
            if self.logger:
                self.logger.info("Successfully set pressure unit to %s", unit)
            return True

        if self.logger:
            self.logger.error("Failed to set unit, response: %s", response)
        raise UnknownResponse(f"Unexpected response: {response}")

    async def get_pressure_unit(self):
        """
        Get the current pressure unit.
        """
        command = b'UNI\r\n'
        if self.logger:
            self.logger.debug("Sending command to get unit: %s", command)
        self.writer.write(command)
        await self.writer.drain()

        if self.logger:
            self.logger.debug("Sending ENQ for unit query")
        self.writer.write(b'\x05')
        await self.writer.drain()

        response = await self.reader.readuntil(b'\r\n')
        unit = response.strip().decode('ascii')
        if self.logger:
            self.logger.info("Current pressure unit: %s", unit)
        return int(unit)


class WrongCommandError(Exception):
    """Raised when an invalid command is sent to the device."""


class UnknownResponse(Exception):
    """Raised when the device returns an unknown response."""


class DeviceConnectionError(Exception):
    """Raised when the device cannot be reached or connected."""
