"""Common base for the HISPEC daemons: transport, broker and config sources."""

import os
from typing import Optional
from urllib.parse import quote

from libby.daemon import LibbyDaemon

# The shared broker, on hispec-new. Its credentials stay out of git: set these
# in /etc/hispec/secrets.env, which is root-only. A host with its own broker
# (e.g. the Palomar cal machine) names it in HISPEC_BROKER_HOST.
BROKER_HOST = "hispec.caltech.edu"
BROKER_HOST_ENV = "HISPEC_BROKER_HOST"
BROKER_USER_ENV = "HISPEC_RABBITMQ_USER"
BROKER_PASSWORD_ENV = "HISPEC_RABBITMQ_PASSWORD"


def broker_url() -> str:
    """Return the shared broker URL, with credentials from the environment."""
    user = os.environ.get(BROKER_USER_ENV)
    password = os.environ.get(BROKER_PASSWORD_ENV)
    host = os.environ.get(BROKER_HOST_ENV) or BROKER_HOST
    if not (user and password):
        return f"amqp://{host}"
    # quote() so a password containing @ or / cannot break the URL apart
    return f"amqp://{quote(user, safe='')}:{quote(password, safe='')}@{host}"


class HispecDaemon(LibbyDaemon):
    """Instantiates the HispecDaemon base using LibbyDaemon.
    Transport is with rabbitmq and discovery is false since rabbitmq includes it's own discovery.
    """

    transport = "rabbitmq"
    discovery_enabled = False

    def config_rabbitmq_url(self) -> str:
        """Return the configured URL if there is one, else the shared broker."""
        return self.rabbitmq_url or broker_url()

    @classmethod
    def from_config_file(cls, path: str, daemon_id: Optional[str] = None, *,
                         env_prefix: Optional[str] = "LIBBY_") -> "HispecDaemon":
        """Build a daemon, applying LIBBY_* environment overrides by default."""
        return super().from_config_file(path, daemon_id, env_prefix=env_prefix)
