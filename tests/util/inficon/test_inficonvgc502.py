import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from hispec.util.inficon.inficonvgc502 import InficonVGC502, UnknownResponse


@pytest.fixture
def vgc502():
    """Creates an InficonVGC502 instance with mock logger."""
    return InficonVGC502(address="127.0.0.1", port=8000, log=False)


@pytest.mark.asyncio
async def test_set_pressure_unit_success(vgc502):
    # Mock reader and writer
    vgc502.reader = AsyncMock()
    vgc502.writer = AsyncMock()

    # Mock the device responding with ACK (\x06\r\n)
    vgc502.reader.readuntil = AsyncMock(return_value=b'\x06\r\n')

    # Call set_pressure_unit
    result = await vgc502.set_pressure_unit(2)  # Pascal
    assert result is True

    # Verify the command was sent
    vgc502.writer.write.assert_any_call(b'UNI,2\r\n')


@pytest.mark.asyncio
async def test_set_pressure_unit_invalid_value(vgc502):
    with pytest.raises(ValueError):
        await vgc502.set_pressure_unit(9)  # Invalid unit


@pytest.mark.asyncio
async def test_set_pressure_unit_unexpected_response(vgc502):
    vgc502.reader = AsyncMock()
    vgc502.writer = AsyncMock()

    # Mock the device responding with something other than ACK
    vgc502.reader.readuntil = AsyncMock(return_value=b'\x15\r\n')

    with pytest.raises(UnknownResponse):
        await vgc502.set_pressure_unit(1)


@pytest.mark.asyncio
async def test_get_pressure_unit(vgc502):
    vgc502.reader = AsyncMock()
    vgc502.writer = AsyncMock()

    # Simulate device sending '3\r\n' for Micron
    vgc502.reader.readuntil = AsyncMock(return_value=b'3\r\n')

    result = await vgc502.get_pressure_unit()
    assert result == 3

    # Ensure UNI and ENQ were written
    vgc502.writer.write.assert_any_call(b'UNI\r\n')
    vgc502.writer.write.assert_any_call(b'\x05')


@pytest.mark.asyncio
async def test_get_pressure_unit_invalid_response(vgc502):
    vgc502.reader = AsyncMock()
    vgc502.writer = AsyncMock()

    # Simulate invalid response
    vgc502.reader.readuntil = AsyncMock(return_value=b'X\r\n')

    with pytest.raises(ValueError):
        # This will raise when trying to convert 'X' to int
        await vgc502.get_pressure_unit()
