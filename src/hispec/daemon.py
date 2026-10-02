"""Common base for the HISPEC daemons: transport, broker and config sources."""

from typing import Optional

from libby.daemon import LibbyDaemon

# The shared broker, on hispec-new; credentials come from LIBBY_RABBITMQ_URL
BROKER_URL = "amqp://hispec.caltech.edu"


class HispecDaemon(LibbyDaemon):
    """Instantiates the HispecDaemon base using LibbyDaemon.
    Transport is with rabbitmq and discovery is false since rabbitmq includes it's own discovery.
    """

    transport = "rabbitmq"
    discovery_enabled = False
    rabbitmq_url = BROKER_URL

    @classmethod
    def from_config_file(cls, path: str, daemon_id: Optional[str] = None, *,
                         env_prefix: Optional[str] = "LIBBY_") -> "HispecDaemon":
        """Build a daemon, applying LIBBY_* environment overrides by default."""
        return super().from_config_file(path, daemon_id, env_prefix=env_prefix)
