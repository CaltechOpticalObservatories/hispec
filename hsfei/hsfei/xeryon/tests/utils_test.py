from ..utils import get_actual_time, get_dpos_epos_string, output_console_factory


def test_get_actual_time_returns_int():
    timestamp = get_actual_time()
    assert isinstance(timestamp, int)


def test_get_dpos_epos_string_format():
    dpos, epos, unit = 123, 456, 'mm'
    result = get_dpos_epos_string(dpos, epos, unit)
    assert result == "DPOS: 123 mm and EPOS: 456 mm"


def test_output_console_prints_info(capsys):
    """Test that output_console logs info messages to stdout."""
    output_console = output_console_factory()
    output_console("Hello from output_console")

    captured = capsys.readouterr()

    assert "Hello from output_console" in captured.out


def test_output_console_prints_err(capsys):
    """Test that output_console logs info messages to stderr."""
    output_console = output_console_factory()
    output_console("Hello from output_console", error=True)

    captured = capsys.readouterr()

    assert "Hello from output_console" in captured.err
