"""Tests for the shared broker URL that HispecDaemon falls back to."""
import pytest

from hispec import daemon


@pytest.fixture(autouse=True)
def fixture_clean_env(monkeypatch):
    """Start every test with none of the broker variables set."""
    for name in (daemon.BROKER_HOST_ENV, daemon.BROKER_USER_ENV, daemon.BROKER_PASSWORD_ENV):
        monkeypatch.delenv(name, raising=False)


def test_default_host():
    """Without HISPEC_BROKER_HOST the shared broker is used."""
    assert daemon.broker_url() == f"amqp://{daemon.BROKER_HOST}"


def test_host_override(monkeypatch):
    """HISPEC_BROKER_HOST replaces the host."""
    monkeypatch.setenv(daemon.BROKER_HOST_ENV, "localhost")
    assert daemon.broker_url() == "amqp://localhost"


def test_host_override_with_credentials(monkeypatch):
    """The credentials still apply to an overridden host, quoted."""
    monkeypatch.setenv(daemon.BROKER_HOST_ENV, "localhost")
    monkeypatch.setenv(daemon.BROKER_USER_ENV, "ops")
    monkeypatch.setenv(daemon.BROKER_PASSWORD_ENV, "p@ss/word")
    assert daemon.broker_url() == "amqp://ops:p%40ss%2Fword@localhost"


def test_empty_host_falls_back(monkeypatch):
    """An empty HISPEC_BROKER_HOST is treated as unset."""
    monkeypatch.setenv(daemon.BROKER_HOST_ENV, "")
    assert daemon.broker_url() == f"amqp://{daemon.BROKER_HOST}"
