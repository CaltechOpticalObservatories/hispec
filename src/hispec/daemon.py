""" Hispec Daemon template """
from __future__ import annotations # for Python 3.9 compatibility
import json
import logging
from dataclasses import is_dataclass, asdict
import collections.abc as cabc
import signal, sys, threading, time
from typing import Any, Callable, Dict, List, Optional, Type

from libby import Libby
from . import config as cfg

Payload = Dict[str, Any]
RPCHandler = Callable[[Payload], Dict[str, Any]]
EvtHandler = Callable[[Payload], None]

class HispecDaemon:
    """
    Base daemon class for Libby peers with support for multiple transports.

    ZMQ Usage:
        class MyPeer(HispecDaemon):
            peer_id = "my-peer"
            bind = "tcp://*:5555"
            address_book = {"other-peer": "tcp://localhost:5556"}

            services = {"echo": lambda payload: {"echo": payload}}
            topics = {"alerts": lambda payload: print(payload)}

    RabbitMQ Usage:
        class MyPeer(HispecDaemon):
            transport = "rabbitmq"
            peer_id = "my-peer"
            rabbitmq_url = "amqp://localhost"  # optional, defaults to this

            services = {"echo": lambda payload: {"echo": payload}}
            topics = {"alerts": lambda payload: print(payload)}

        Note: RabbitMQ doesn't need bind or address_book since routing is
        handled automatically by the broker.
    """
    # simple attributes users set
    peer_id: Optional[str] = None
    bind: Optional[str] = None
    address_book: Optional[Dict[str, str]] = None
    discovery_enabled: bool = True
    discovery_interval_s: float = 5.0

    # transport selection: "zmq" or "rabbitmq (default)"
    transport: str = "rabbitmq"
    rabbitmq_url: Optional[str] = None
    group_id: Optional[str] = None
    # internal config
    _config: Dict[str, Any] = {}

    # payload-only handlers
    services: Dict[str, RPCHandler] = {}
    topics: Dict[str, EvtHandler] = {}

    def __init__(self) -> None:
        # Ensure per-instance handler tables
        if type(self).services is self.services:
            self.services = {}
        if type(self).topics is self.topics:
            self.topics = {}

    # Config ingestion
    @classmethod
    def from_config_file(
        cls: Type["HispecDaemon"],
        path: str,
        daemon_id: Optional[str] = None,
    ) -> "HispecDaemon":
        """
        Build a daemon from a YAML config file.

        Args:
            path: Path to yaml config file
            daemon_id: For subsystem configs, which daemon to instantiate.
                      If None and config has multiple daemons, raises error.

        Returns:
            Configured daemon instance
        """
        loader = cfg.DaemonConfigLoader(path)

        # For subsystem configs, daemon_id is required unless only one daemon
        if loader.is_subsystem:
            if daemon_id is None:
                if len(loader.daemon_ids) == 1:
                    daemon_id = loader.daemon_ids[0]
                else:
                    raise cfg.ConfigError(
                        f"Subsystem config has multiple daemons: {loader.daemon_ids}. "
                        f"Specify daemon_id parameter."
                    )

        config_dict = loader.get_daemon_config(daemon_id)
        return cls.from_config(config_dict)

    @classmethod
    def from_config(cls: Type["HispecDaemon"], config: Dict[str, Any]) -> "HispecDaemon":
        """
        Build a daemon from a configuration dictionary.

        Known daemon attributes are mapped directly to instance attributes.

        Args:
            config: Configuration dictionary

        Returns:
            Configured daemon instance
        """
        instance = cls()

        # Map known daemon attributes directly
        for attr in cfg.DAEMON_ATTRS:
            if attr in config:
                setattr(instance, attr, config[attr])

        # Store full config for subclass access
        instance._config = config

        # Setup logging
        instance._setup_logging()

        return instance

    def _setup_logging(self) -> None:
        """Configure logging from config or defaults."""
        log_config = self._config.get("logging", {})
        level_str = log_config.get("level", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        log_file = log_config.get("file")

        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=log_file,
        )

        self.logger = logging.getLogger(self.peer_id or self.__class__.__name__)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the daemon's configuration.

        Args:
            key: Config key (supports dot notation for nested keys, e.g., "hardware.ip_address")
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


    # optional hooks
    def on_start(self, libby: Libby) -> None: ...
    def on_stop(self, libby: Optional[Libby] = None) -> None: ...
    def on_hello(self, libby: Libby) -> None: ...
    def on_event(self, topic: str, msg) -> None:
        print(f"[{self.__class__.__name__}] {topic}: {msg.env.payload}")

    # config getters
    def config_peer_id(self) -> str: return self.peer_id or self._must("peer_id")
    def config_bind(self) -> str: return self.bind or self._must("bind")
    def config_rabbitmq_url(self) -> str: return self.rabbitmq_url or "amqp://localhost"
    def config_group_id(self) -> Optional[str]: return self.group_id
    def config_address_book(self) -> Dict[str, str]: return self.address_book if self.address_book is not None else {}
    def config_discovery_enabled(self) -> bool: return bool(self.discovery_enabled)
    def config_discovery_interval_s(self) -> float: return float(self.discovery_interval_s)
    def config_rpc_keys(self) -> List[str]: return list(self.services.keys())
    def config_subscriptions(self) -> List[str]: return list(self.topics.keys())

    # user-facing helpers
    def add_service(self, key: str, fn: RPCHandler) -> None:
        self.services[key] = fn
        if hasattr(self, "libby"): self._register_services({key: fn})

    def add_services(self, mapping: Dict[str, RPCHandler]) -> None:
        self.services.update(mapping)
        if hasattr(self, "libby"): self._register_services(mapping)

    def add_topic(self, topic: str, fn: EvtHandler) -> None:
        self.topics[topic] = fn
        if hasattr(self, "libby"):
            self.libby.listen(topic, lambda msg, _h=fn: _h(msg.env.payload))
            self.libby.subscribe(topic)

    def add_topics(self, mapping: Dict[str, EvtHandler]) -> None:
        self.topics.update(mapping)
        if hasattr(self, "libby"):
            for topic, fn in mapping.items():
                self.libby.listen(topic, lambda msg, _h=fn: _h(msg.env.payload))
            self.libby.subscribe(*mapping.keys())

    # internals
    def _must(self, name: str):
        raise NotImplementedError(f"Set `{name}` or override config_{name}()")

    def _service_adapter(self, fn):
        def adapter(user_payload: dict, _ctx: dict) -> dict:
            try:
                result = fn(user_payload)      # user returns ANYTHING
                return self.payload(result)    # we "shove it into payload" for them
            except Exception as ex:
                return {"ok": False, "error": str(ex)}
        return adapter

    def _register_services(self, mapping: Dict[str, RPCHandler]) -> None:
        for key, fn in mapping.items():
            self.libby.serve_keys([key], self._service_adapter(fn))

    def build_libby(self) -> Libby:
        """Build Libby instance with selected transport."""
        if self.transport == "rabbitmq":
            return Libby.rabbitmq(
                self_id=self.config_peer_id(),
                rabbitmq_url=self.config_rabbitmq_url(),
                keys=[],
                callback=None,
                group_id=self.config_group_id(),
            )
        else:
            # Default to ZMQ
            return Libby.zmq(
                self_id=self.config_peer_id(),
                bind=self.config_bind(),
                address_book=self.config_address_book(),
                keys=[], callback=None,                     # register per-key
                discover=self.config_discovery_enabled(),
                discover_interval_s=self.config_discovery_interval_s(),
                hello_on_start=True,
                group_id=self.config_group_id(),
            )

    def serve(self) -> None:
        stop_evt = threading.Event()
        def _sig(_s, _f): stop_evt.set()
        signal.signal(signal.SIGINT, _sig)
        signal.signal(signal.SIGTERM, _sig)

        try:
            self.libby = self.build_libby()
        except Exception as ex:
            print(f"[{self.__class__.__name__}] failed to start: {ex}", file=sys.stderr)
            raise

        if self.services:
            self._register_services(self.services)
        if self.topics:
            for topic, fn in self.topics.items():
                self.libby.listen(topic, lambda msg, _h=fn: _h(msg.env.payload))
            self.libby.subscribe(*self.topics.keys())

        # discovery hello + hooks
        try:
            if self.config_discovery_enabled():
                self.libby.hello()
                self.on_hello(self.libby)
        except Exception:
            pass

        try:
            self.on_start(self.libby)
        except Exception as ex:
            print(f"[{self.__class__.__name__}] on_start error: {ex}", file=sys.stderr)

        if self.transport == "rabbitmq":
            print(f"[{self.__class__.__name__}] up: id={self.config_peer_id()} transport=rabbitmq url={self.rabbitmq_url}")
        else:
            print(f"[{self.__class__.__name__}] up: id={self.config_peer_id()} bind={self.config_bind()}")
        try:
            while not stop_evt.is_set(): time.sleep(0.5)
        finally:
            try: self.on_stop()
            except Exception: pass
            self.libby.stop()
            print(f"[{self.__class__.__name__}] stopped")

    def payload(self, value=None, /, **extra) -> dict:
        if value is None:
            out = {}
        elif is_dataclass(value):
            out = asdict(value)
        elif isinstance(value, cabc.Mapping):
            out = dict(value)
        else:
            out = {"data": value}

        if extra:
            out.update(extra)

        try:
            json.dumps(out)
        except TypeError as e:
            raise ValueError(f"Payload not JSON-serializable: {e}") from e

        return out