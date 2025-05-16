import asyncio
import sys

class InficonVGC502:
    def __init__(self, address, port, timeout=1):
        self.address = address
        self.port = int(port)
        self.timeout = timeout
        self.reader = None
        self.writer = None

    async def __aenter__(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.address, self.port)
        except ConnectionRefusedError as err:
            print(f"Connection refused: {err}")
            sys.exit(1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def read_pressure(self, gauge=1):
        """Send pressure read command and parse response."""
        command = f'PR{gauge}\r\n'.encode('ascii')
        self.writer.write(command)
        await self.writer.drain()

        acknowledgment = await self.reader.readuntil(b'\r\n')
        acknowledgment = acknowledgment.strip()

        if acknowledgment == b'\x06':  # ACK
            self.writer.write(b'\x05')  # ENQ
            await self.writer.drain()
            response = await self.reader.readuntil(b'\r\n')
            response_str = response.strip().decode('ascii')
            try:
                return float(response_str.split(',')[1])
            except (IndexError, ValueError):
                return sys.float_info.max
        elif acknowledgment == b'\x15':  # NAK
            raise WrongCommandError("Wrong command sent.")
        else:
            raise UnknownResponse(f"Unknown response: {acknowledgment}")

class WrongCommandError(Exception):
    """Raised when the device responds with a NAK (wrong command)."""
    pass

class UnknownResponse(Exception):
    """Raised when the device responds with an unknown acknowledgement."""
    pass
