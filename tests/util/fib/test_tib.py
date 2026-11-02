"""Tests for the TIB driver and its transport, against a fake MQTT client."""

import json
from types import SimpleNamespace

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from hispec.driver.fib import (FibCommandError, FibError, FibRefusedError, FibTimeoutError,
                               LaserSummary, MemsSwitch, TrunkInterfaceBox)
from hispec.driver.fib.transport import query_payload

DEVICE = "hsfib-tib"

# Replies captured from the TIB, firmware 1cc662bfd7da
STATUS = {"fw": "1cc662bfd7da-dirty", "boots": 9, "board": "tib", "board_ok": True,
          "mems_switches": 8, "relay_err": 0, "amb_c": 21.562, "pd_on_s": 833,
          "laserbank_on_s": 6196,
          "lastcmd": {"name": "pd/dark/yj", "src": "mqtt", "t_ms": 6266718}}
MEMS = {"yj_forward_retro": {"state": "A"}, "yj_ao_fei": {"state": "B"},
        "hk_mm_sm": {"state": "A", "duty_cycle": 0.5}}
ROUTES = {"active_routes": {"yj_ao": ["no source"], "yj_fei": ["yj_1430", "yj_laser"],
                            "yj_pd": ["yj_sm"]}}
OPTIONS = {"board": "tib", "lasers": ["1028y", "1270j"], "route_inputs": ["yj_1430", "yj_cal"],
           "route_outputs": ["yj_ao", "yj_fei"], "routes": [["yj_1430", "yj_ao"]]}
LASERS = {"1028y": {"power_mw": 0.0, "ready": True, "tec_on_s": None, "off_in_s": None},
          "1270j": {"power_mw": None, "ready": False, "tec_on_s": 12, "off_in_s": 288}}
ATTENS = {"1028y": {"value_db": 3.5}, "1270j": {"value_db": None}}

REFUSED_KEYS = ["laser", "laser/status", "laser/tune", "laser/settings", "laser/bankpower",
                "laser/bankpower/override_on", "laser/bankheater/auto", "laser/clearfaults",
                "measure_throughput", "atten/1028y", "atten/calibrate", "pd", "pd/yj",
                "pd/dark/yj", "reboot", "mems/route/loss", "mems/split", "status/x", ""]


def status_reply(payload):
    """Answer ``status`` like the board, adding the requested optional sections."""
    options = json.loads(payload) if payload else {}
    reply = dict(STATUS)
    if options.get("lasers"):
        reply["lasers"] = LASERS
    if options.get("attens"):
        reply["attens"] = ATTENS
    return reply


def unset_callback(*_args):
    """Stand in for a paho callback the transport has not assigned yet."""
    raise AssertionError("callback not assigned")


class FakeMqttClient:
    """Stand-in for paho's client that answers each request from a reply table."""

    def __init__(self, replies):
        self.replies = replies
        self.published = []
        self.subscriptions = []
        self.on_connect = self.on_disconnect = self.on_message = unset_callback

    def enable_logger(self, _logger):
        """Accept paho's logger hook."""

    def connect(self, host, port, keepalive):
        """Record the broker address."""
        self.address = (host, port, keepalive)  # pylint: disable=attribute-defined-outside-init

    def loop_start(self):
        """Complete the connection the way paho's network thread would."""
        self.on_connect(self, None, None, ReasonCode(PacketTypes.CONNACK, "Success"), None)

    def loop_stop(self):
        """Nothing to stop."""

    def disconnect(self):
        """Nothing to close."""

    def subscribe(self, topics):
        """Record the subscriptions."""
        self.subscriptions.extend(topic for topic, _qos in topics)

    def publish(self, topic, payload, qos, retain, properties):  # pylint: disable=too-many-arguments
        """Record the request and answer it if the table has a reply."""
        self.published.append(SimpleNamespace(topic=topic, payload=payload, qos=qos,
                                              retain=retain, properties=properties))
        reply = self.replies.get(topic.removeprefix(f"cmd/{DEVICE}/req/"))
        if callable(reply):
            reply = reply(payload)
        if reply is not None:
            self.deliver(properties.ResponseTopic, reply, properties.CorrelationData)
        return SimpleNamespace(rc=mqtt.MQTT_ERR_SUCCESS)

    def deliver(self, topic, payload, correlation=None):
        """Hand a message to the transport as paho's network thread would."""
        message = mqtt.MQTTMessage(topic=topic.encode())
        message.payload = json.dumps(payload).encode()
        message.properties = Properties(PacketTypes.PUBLISH)
        if correlation is not None:
            message.properties.CorrelationData = correlation
        self.on_message(self, None, message)


@pytest.fixture(name="fake")
def fixture_fake():
    """Return a fake client answering every TIB query the driver makes."""
    return FakeMqttClient({"status": status_reply, "mems": MEMS, "mems/route": ROUTES,
                           "help/options": OPTIONS, "time": {"utc": 1, "uptime_s": 2},
                           "temps": {"ambient_c": 21.5, "laserbank_c": None,
                                     "lasers": {"1028y": 19.0}}})


@pytest.fixture(name="tib")
def fixture_tib(fake):
    """Return a TIB connected through the fake client."""
    box = TrunkInterfaceBox(timeout_s=0.05, client_factory=lambda: fake, log=False)
    box.connect(DEVICE, "broker.example")
    return box


@pytest.mark.parametrize("key", REFUSED_KEYS)
def test_refuses_everything_outside_allowlist(key):
    """Refuse laser, attenuator, photodiode, throughput and reboot endpoints"""
    with pytest.raises(FibRefusedError):
        query_payload(key)


@pytest.mark.parametrize("options", [{"value": True}, {"lasers": 1}, {"name": "1028y"}])
def test_refuses_status_options_outside_allowlist(options):
    """Refuse status options that are not the documented flags"""
    with pytest.raises(FibRefusedError):
        query_payload("status", options)


def test_refuses_options_on_other_queries():
    """Refuse a payload on any query other than status"""
    with pytest.raises(FibRefusedError):
        query_payload("mems", {"lasers": True})


def test_refused_query_publishes_nothing(tib, fake):
    """Raise before anything reaches the broker"""
    published = len(fake.published)
    with pytest.raises(FibRefusedError):
        tib.query("laser", {"lasers": True})
    assert len(fake.published) == published


def test_every_driver_query_is_allowlisted_and_unretained(tib, fake):
    """Keep every driver read inside the allowlist and unretained"""
    for read in (tib.board_status, tib.time, tib.options, tib.mems, tib.active_routes, tib.temps,
                 tib.lasers, tib.attenuations_db):
        read()
    for request in fake.published:
        key = request.topic.removeprefix(f"cmd/{DEVICE}/req/")
        options = json.loads(request.payload) if request.payload else None
        assert query_payload(key, options) == request.payload
        assert not request.retain
        assert len(request.properties.CorrelationData) == 16


def test_connect_subscribes_to_replies_and_events(fake, tib):
    """Subscribe to replies, warnings and boot events only"""
    assert tib.is_connected()
    assert set(fake.subscriptions) == {f"cmd/{DEVICE}/resp/#", f"dt/{DEVICE}/warning",
                                       f"dt/{DEVICE}/boot"}


def test_connect_rejects_other_board_profile(fake):
    """Fail connect when the device reports another board profile"""
    fake.replies["status"] = dict(STATUS, board="as")
    box = TrunkInterfaceBox(timeout_s=0.05, client_factory=lambda: fake, log=False)
    with pytest.raises(FibError, match="expected 'tib'"):
        box.connect(DEVICE, "broker.example")
    assert not box.is_connected()


def test_status(tib):
    """Parse the status reply"""
    status = tib.board_status()
    assert status.firmware == "1cc662bfd7da-dirty"
    assert status.ambient_c == pytest.approx(21.562)
    assert status.laser_bank_on_s == 6196
    assert status.last_command.name == "pd/dark/yj"


def test_mems_and_routes(tib):
    """Parse switch states and drop the no-source marker from routes"""
    assert tib.mems()["hk_mm_sm"] == MemsSwitch("A", 0.5)
    assert tib.mems()["yj_ao_fei"] == MemsSwitch("B")
    routes = tib.active_routes()
    assert routes["yj_ao"] == ()
    assert routes["yj_fei"] == ("yj_1430", "yj_laser")


def test_options(tib):
    """Parse the profile's names"""
    options = tib.options()
    assert options.lasers == ("1028y", "1270j")
    assert options.routes == (("yj_1430", "yj_ao"),)


def test_lasers_and_attenuations(tib, fake):
    """Request only the lasers section and parse nulls"""
    assert tib.lasers()["1270j"] == LaserSummary(None, False, 12, 288)
    assert json.loads(fake.published[-1].payload) == {"lasers": True}
    assert tib.attenuations_db() == {"1028y": 3.5, "1270j": None}


def test_temps(tib):
    """Parse temperatures with a null laser bank reading"""
    temps = tib.temps()
    assert temps.laser_bank_c is None
    assert temps.lasers == {"1028y": 19.0}


def test_board_error_raises(tib, fake):
    """Raise the board's error text"""
    fake.replies["temps"] = {"error": "busy"}
    with pytest.raises(FibCommandError, match="temps: busy"):
        tib.temps()


def test_unanswered_query_times_out(tib, fake):
    """Time out and forget the pending query"""
    del fake.replies["time"]
    with pytest.raises(FibTimeoutError):
        tib.time()
    assert not tib._transport._pending  # pylint: disable=protected-access


def test_ignores_replies_to_other_clients(tib, fake):
    """Ignore replies whose correlation data is not ours"""
    fake.replies["time"] = None
    pending = tib._transport.send("time")  # pylint: disable=protected-access
    fake.deliver(f"cmd/{DEVICE}/resp/time", {"utc": 9, "uptime_s": 9}, b"someone else")
    fake.deliver(f"cmd/{DEVICE}/resp/time", {"utc": 9, "uptime_s": 9})
    assert not pending.future.done()
    fake.deliver(f"cmd/{DEVICE}/resp/time", {"utc": 1, "uptime_s": 2}, pending.correlation)
    assert pending.future.result(0) == {"utc": 1, "uptime_s": 2}


def test_warning_reaches_callback(tib, fake):
    """Forward board warnings to the callback"""
    events = []
    tib.on_warning = events.append
    warning = {"severity": "warning", "code": "attenuator_clamped", "msg": "m", "context": "c",
               "uptime_ms": 5}
    fake.deliver(f"dt/{DEVICE}/warning", warning)
    assert events == [warning]


def test_disconnect_fails_waiting_queries(tib, fake):
    """Fail queries still waiting when disconnecting"""
    fake.replies["time"] = None
    pending = tib._transport.send("time")  # pylint: disable=protected-access
    tib.disconnect()
    with pytest.raises(FibError, match="closed"):
        pending.future.result(0)
    assert not tib.is_connected()
