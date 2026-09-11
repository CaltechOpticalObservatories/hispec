"""Driver doubles, so FEI procedures can be tested without hardware.

Each double covers only the calls the API layer makes, and records them, so a
test can assert on the order a procedure issued its driver calls. Real device
configs from ``config/hsfei/`` are used, which keeps the axis and named-position
plumbing honest.
"""
import pytest

from hispec.api.fei import FEI, devices


class FakePi:
    """Stands in for ``PIControllerBase``, one instance per controller."""

    def __init__(self):
        self.positions = {}
        self.moving = set()
        self.homed = set()
        self.refuse_moves = False
        self.calls = []

    def _key(self, device_key, axis):
        return (device_key, str(axis))

    def set_pos(self, pos, device_key=None, axis=None, blocking=True, timeout=20):
        self.calls.append(("set_pos", self._key(device_key, axis), pos, blocking))
        if self.refuse_moves:
            return False
        self.positions[self._key(device_key, axis)] = pos
        return True

    def get_pos(self, device_key=None, axis=None):
        return self.positions.get(self._key(device_key, axis), 0.0)

    def is_moving(self, device_key, axis):
        return self._key(device_key, axis) in self.moving

    def is_homed(self, device_key=None, axis=None):
        return self._key(device_key, axis) in self.homed

    def home(self, device_key=None, axis=None, method="FRF", blocking=True, timeout=20):
        self.calls.append(("home", self._key(device_key, axis)))
        self.homed.add(self._key(device_key, axis))
        return True

    def halt_motion(self, device_key):
        self.calls.append(("halt_motion", device_key))
        return True

    def is_connected(self):
        return True

    def disconnect(self):
        self.calls.append(("disconnect",))


class FakeNewport:
    """Stands in for the SMC100PP ``StageController`` driving the ADC prisms."""

    def __init__(self):
        self.positions = {1: 0.0, 2: 0.0}
        self.moving = set()
        self.homed = set()
        self.refuse_moves = False
        self.calls = []

    def move_abs(self, position=None, stage_id=None, blocking=False):
        self.calls.append(("move_abs", stage_id, position, blocking))
        if self.refuse_moves:
            return False
        self.positions[stage_id] = position
        return True

    def get_pos(self, stage_id=1):
        return self.positions.get(stage_id)

    def get_state(self, stage_id=1):
        return "MOVING" if stage_id in self.moving else "READY"

    def is_homed(self, stage_id=1):
        return stage_id in self.homed

    def home(self, stage_id=1):
        self.calls.append(("home", stage_id))
        self.homed.add(stage_id)
        return True

    def is_connected(self):
        return True

    def disconnect(self):
        self.calls.append(("disconnect",))


class FakeThermal:
    """Stands in for ``LakeshoreController``."""

    def __init__(self, temperatures=None):
        self.temperatures = temperatures or {}

    def get_temperature(self, sensor):
        if sensor not in self.temperatures:
            raise OSError(f"no sensor {sensor}")
        return self.temperatures[sensor]

    def get_heater_setpoint(self, output):
        return 10.0 * int(output)

    def get_heater_output(self, output):
        return 5.0 * int(output)

    def is_connected(self):
        return True

    def disconnect(self):
        pass


class FakePressure:
    """Stands in for ``InficonVGC502``."""

    def read_pressure(self, gauge=1):
        return 1e-6 * gauge

    def read_temperature(self):
        return 22.5

    def is_connected(self):
        return True

    def disconnect(self):
        pass


class FakeCryo:
    """Stands in for ``SunpowerCryocooler``."""

    def __init__(self, cold_head_temps=None):
        # Successive get_cold_head_temp() calls walk this list, so a test can
        # describe a dewar that cools over several samples.
        self.cold_head_temps = list(cold_head_temps or [80.0])
        self.target_temp = None
        self.cooler_on = False
        self.calls = []

    def get_cold_head_temp(self):
        if len(self.cold_head_temps) > 1:
            return self.cold_head_temps.pop(0)
        return self.cold_head_temps[0]

    def get_reject_temp(self):
        return 300.0

    def get_target_temp(self):
        return self.target_temp

    def get_measured_power(self):
        return 120.0

    def get_commanded_power(self):
        return 150.0

    def get_control_mode(self):
        return "TEMP"

    def get_error(self):
        return "000000"

    def set_target_temp(self, temp_kelvin):
        self.calls.append(("set_target_temp", temp_kelvin))
        self.target_temp = temp_kelvin
        return temp_kelvin

    def turn_on_cooler(self):
        self.calls.append(("turn_on_cooler",))
        self.cooler_on = True
        return "ON"

    def is_connected(self):
        return True

    def disconnect(self):
        pass


class FakePositional:
    """Stands in for the filter wheel and the PIAA gimbal controllers."""

    def __init__(self, position=1):
        self.position = position

    def get_pos(self, channel=1):
        return self.position + channel - 1

    def is_connected(self):
        return True

    def disconnect(self):
        pass


@pytest.fixture(name="fake_drivers")
def fake_drivers_fixture():
    """Return one double per HSFEI device, keyed by device name."""
    return {
        devices.ADC: FakeNewport(),
        devices.ATCCRYO: FakeCryo(),
        devices.ATCFW: FakePositional(),
        devices.ATCL: FakePi(),
        devices.ATCP: FakePi(),
        devices.ATCPRESS: FakePressure(),
        devices.ATCTHERM: FakeThermal({"A": 40.0, "B": 41.0}),
        devices.FEIPO: FakePi(),
        devices.LSM: FakePi(),
        devices.MS: FakePi(),
        devices.PIAAGIMB: FakePositional(),
        devices.PIAAGIMR: FakePositional(),
    }


@pytest.fixture(name="fei")
def fei_fixture(fake_drivers):
    """An FEI reading the real config/hsfei/ files, wired to the doubles."""
    api = FEI()
    for device, driver in fake_drivers.items():
        api.attach(device, driver)
    return api
