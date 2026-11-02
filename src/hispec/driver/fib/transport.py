"""MQTT 5 request/response transport for one FIB PCB."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any, Final

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

DEFAULT_PORT: Final = 1883
CONNECT_TIMEOUT_S: Final = 5.0
KEEPALIVE_S: Final = 30

# Allow only payload-free queries, so no request can drive a laser or change hardware state
QUERY_KEYS: Final = frozenset({
    "help", "help/options", "status", "time", "ip", "mqtt", "serialguard",
    "mems", "mems/route", "temps", "mems/split/yj", "mems/split/hk",
})
MEMS_SWITCH_KEY: Final = re.compile(r"mems/(yj|hk)_[a-z0-9_]+")
STATUS_OPTIONS: Final = frozenset({"ip", "lasers", "attens"})

Reply = dict[str, Any]
EventCallback = Callable[[Reply], None]


class FibError(RuntimeError):
    """Failure talking to a FIB PCB."""


class FibRefusedError(FibError):
    """Request outside the query allowlist, refused before publishing."""


class FibTimeoutError(FibError):
    """No reply from the board within the timeout."""


class FibCommandError(FibError):
    """Board replied with an error."""

    def __init__(self, key: str, reply: Reply) -> None:
        super().__init__(f"{key}: {reply['error']}")
        self.key = key
        self.reply = reply


@dataclass(frozen=True)
class PendingQuery:
    """A published query waiting for its correlated reply."""

    key: str
    correlation: bytes
    future: Future[Reply] = field(default_factory=Future)


def query_payload(key: str, options: Mapping[str, bool] | None = None) -> bytes | None:
    """Return the payload for an allowlisted query, refusing anything else."""
    if key not in QUERY_KEYS and not MEMS_SWITCH_KEY.fullmatch(key):
        raise FibRefusedError(f"{key!r} is not an allowed query")
    if not options:
        return None
    valid_options = (
        key == "status"
        and set(options) <= STATUS_OPTIONS
        and all(isinstance(value, bool) for value in options.values())
    )
    if not valid_options:
        raise FibRefusedError(f"options {dict(options)} are not allowed on {key!r}")
    return json.dumps(dict(options)).encode()


def _new_paho_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    # Log callback exceptions instead of letting them kill the network thread
    client.suppress_exceptions = True
    return client


class FibPcbClient:  # pylint: disable=too-many-instance-attributes
    """Send queries to one FIB PCB and match each reply by its correlation data."""

    def __init__(self, device: str, broker: str, port: int = DEFAULT_PORT,
                 client_factory: Callable[[], mqtt.Client] | None = None,
                 logger: logging.Logger | None = None) -> None:
        self.device = device
        self.broker = broker
        self.port = port
        self.on_warning: EventCallback | None = None
        self.on_boot: EventCallback | None = None
        self._logger = logger or logging.getLogger(__name__)
        self._connected = threading.Event()
        self._pending: dict[bytes, Future[Reply]] = {}
        self._pending_lock = threading.Lock()
        self._client = (client_factory or _new_paho_client)()
        self._client.enable_logger(self._logger)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message

    @property
    def is_open(self) -> bool:
        """Return True while the broker connection is up."""
        return self._connected.is_set()

    def open(self, timeout_s: float = CONNECT_TIMEOUT_S) -> None:
        """Connect to the broker and subscribe to this board's replies and events."""
        self._client.connect(self.broker, self.port, keepalive=KEEPALIVE_S)
        self._client.loop_start()
        if not self._connected.wait(timeout_s):
            self.close()
            raise FibError(f"no MQTT connection to {self.broker}:{self.port} "
                           f"within {timeout_s} s")

    def close(self) -> None:
        """Disconnect from the broker and fail any query still waiting."""
        self._client.disconnect()
        self._client.loop_stop()
        self._connected.clear()
        self._fail_pending(FibError("MQTT connection closed"))

    def send(self, key: str, options: Mapping[str, bool] | None = None) -> PendingQuery:
        """Publish one allowlisted query and return a handle for its reply."""
        payload = query_payload(key, options)
        if not self.is_open:
            raise FibError(f"not connected to {self.broker}:{self.port}")
        pending = PendingQuery(key, uuid.uuid4().bytes)
        with self._pending_lock:
            self._pending[pending.correlation] = pending.future
        properties = Properties(PacketTypes.PUBLISH)
        properties.ResponseTopic = f"cmd/{self.device}/resp/{key}"
        properties.CorrelationData = pending.correlation
        info = self._client.publish(f"cmd/{self.device}/req/{key}", payload,
                                    qos=0, retain=False, properties=properties)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            self._discard(pending)
            raise FibError(f"publishing {key} failed: {mqtt.error_string(info.rc)}")
        return pending

    def result(self, pending: PendingQuery, timeout_s: float) -> Reply:
        """Wait for the reply to a sent query."""
        try:
            return pending.future.result(timeout_s)
        except TimeoutError as error:
            raise FibTimeoutError(f"no reply to {pending.key} from {self.device} "
                                  f"within {timeout_s} s") from error
        finally:
            self._discard(pending)

    def _discard(self, pending: PendingQuery) -> None:
        with self._pending_lock:
            self._pending.pop(pending.correlation, None)

    def _fail_pending(self, error: FibError) -> None:
        with self._pending_lock:
            futures = list(self._pending.values())
            self._pending.clear()
        for future in futures:
            if not future.done():
                future.set_exception(error)

    def _handle_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any,
                        reason_code: Any, _properties: Any) -> None:
        if reason_code.is_failure:
            self._logger.error("MQTT connect to %s refused: %s", self.broker, reason_code)
            return
        # Subscribe here so a reconnect restores the subscriptions
        client.subscribe([(f"cmd/{self.device}/resp/#", 0),
                          (f"dt/{self.device}/warning", 0),
                          (f"dt/{self.device}/boot", 0)])
        self._connected.set()

    def _handle_disconnect(self, _client: mqtt.Client, _userdata: Any, _flags: Any,
                           reason_code: Any, _properties: Any) -> None:
        self._connected.clear()
        self._fail_pending(FibError(f"MQTT connection lost: {reason_code}"))

    def _handle_message(self, _client: mqtt.Client, _userdata: Any,
                        message: mqtt.MQTTMessage) -> None:
        if message.topic.startswith(f"dt/{self.device}/"):
            self._dispatch_event(message)
            return
        correlation = getattr(message.properties, "CorrelationData", None)
        with self._pending_lock:
            future = self._pending.pop(correlation, None)
        # Replies to other clients' requests share the default response topic
        if future is None or future.done():
            return
        key = message.topic.removeprefix(f"cmd/{self.device}/resp/")
        try:
            reply = json.loads(message.payload)
        except json.JSONDecodeError as error:
            future.set_exception(FibError(f"{key}: undecodable reply {message.payload!r}: {error}"))
            return
        if isinstance(reply, dict) and "error" in reply:
            future.set_exception(FibCommandError(key, reply))
        else:
            future.set_result(reply)

    def _dispatch_event(self, message: mqtt.MQTTMessage) -> None:
        callback = self.on_boot if message.topic.endswith("/boot") else self.on_warning
        try:
            event = json.loads(message.payload)
        except json.JSONDecodeError:
            self._logger.warning("undecodable event on %s: %r", message.topic, message.payload)
            return
        if callback is not None:
            callback(event)
