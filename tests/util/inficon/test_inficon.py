import pytest
from util.inficon.inficonvgc502 import InficonVGC502, WrongCommandError, UnknownResponse


@pytest.mark.asyncio
async def test_read_pressure():
    # Replace with your Inficon device address and port
    INFICON_ADDRESS = "127.0.0.1"
    INFICON_PORT = 8000

    try:
        # Connect to the device and read pressure from gauge 1
        async with InficonVGC502(INFICON_ADDRESS, INFICON_PORT) as inficon:
            pressure = await inficon.read_pressure(gauge=1)
            print(f"Pressure from Gauge 1: {pressure} Torr")
            assert isinstance(pressure, float)  # Assert that pressure is a float

    except (WrongCommandError, UnknownResponse) as e:
        pytest.fail(f"Error: {e}")  # Fail the test if any of these exceptions occur
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")