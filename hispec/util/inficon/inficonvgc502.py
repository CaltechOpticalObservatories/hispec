import asyncio
import sys
import hispec.util.helper.logger_utils as logger_utils


class InficonVGC502:
    def __init__(self, address, port, timeout=1, log=True, quiet=False):
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
                self.logger.info(f"Connected to {self.address}:{self.port}")
        except ConnectionRefusedError as err:
            if self.logger:
                self.logger.error(f"Connection refused: {err}")
            raise DeviceConnectionError(f"Could not connect to {self.address}:{self.port}") from err
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            if self.logger:
                self.logger.info("Connection closed")

    async def read_pressure(self, gauge=1):
        command = f'PR{gauge}\r\n'.encode('ascii')
        if self.logger:
            self.logger.debug(f"Sending command: {command}")
        self.writer.write(command)
        await self.writer.drain()

        try:
            acknowledgment = await self.reader.readuntil(b'\r\n')
            acknowledgment = acknowledgment.strip()
            if self.logger:
                self.logger.debug(f"Acknowledgment received: {acknowledgment}")
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
                    self.logger.debug(f"Pressure response: {response_str}")
                return float(response_str.split(',')[1])
            except (IndexError, ValueError) as e:
                if self.logger:
                    self.logger.error(f"Failed to parse response: {e}")
                return sys.float_info.max
        elif acknowledgment == b'\x15':
            if self.logger:
                self.logger.error("Received NAK: Wrong command")
            raise WrongCommandError("Wrong command sent.")
        else:
            if self.logger:
                self.logger.error(f"Unknown acknowledgment: {acknowledgment}")
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
            self.logger.debug(f"Sending command to set unit: {command}")
        self.writer.write(command)
        await self.writer.drain()

        response = await self.reader.readuntil(b'\r\n')
        response = response.strip()
        if self.logger:
            self.logger.debug(f"Response to set unit: {response}")

        if response == b'\x06':
            if self.logger:
                self.logger.info(f"Successfully set pressure unit to {unit}")
            return True
        else:
            if self.logger:
                self.logger.error(f"Failed to set unit, response: {response}")
            raise UnknownResponse(f"Unexpected response: {response}")

    async def get_pressure_unit(self):
        """
        Get the current pressure unit.
        """
        command = b'UNI\r\n'
        if self.logger:
            self.logger.debug(f"Sending command to get unit: {command}")
        self.writer.write(command)
        await self.writer.drain()

        if self.logger:
            self.logger.debug("Sending ENQ for unit query")
        self.writer.write(b'\x05')
        await self.writer.drain()

        response = await self.reader.readuntil(b'\r\n')
        unit = response.strip().decode('ascii')
        if self.logger:
            self.logger.info(f"Current pressure unit: {unit}")
        return int(unit)


class WrongCommandError(Exception):
    pass


class UnknownResponse(Exception):
    pass


class DeviceConnectionError(Exception):
    pass
