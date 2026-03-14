"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
import pytest
from click.testing import CliRunner
from . import buoys_file_gpx, buoys_file_list, buoys_file_describe, buoys_file_export, buoys_plot_daily, buoys_plot_tail, buoys_firmware_library, buoys_firmware_template

by_station = pytest.mark.parametrize("name", ["wynken", "blynken"])
by_observed_property = pytest.mark.parametrize("observed_property", ["sea_water_salinity", "sea_water_temperature"])
runner = CliRunner()

def test_cli_buoys_file_list():
    """
    List available stations
    """
    result = runner.invoke(buoys_file_list)
    assert result.exit_code == 0
    assert "Wynken" in result.output

@by_station
@pytest.mark.parametrize("table", ["sonde", "diagnostic"])
def test_cli_buoys_file_describe(name, table):
    """
    Expect command line output
    """
    result = runner.invoke(buoys_file_describe, [name, table])
    assert result.exit_code == 0

@by_station
@pytest.mark.parametrize("table", ["sonde", "diagnostic"])
def test_cli_buoys_file_export(name, table):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_file_export, [name, table])
    assert result.exit_code == 0

@by_station
def test_cli_buoys_file_gpx(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_file_gpx, [name])
    assert result.exit_code == 0

@by_station
@by_observed_property
def test_cli_buoys_plot_tail(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_plot_tail, [name, "sonde", observed_property])
    assert result.exit_code == 0

@by_station
@by_observed_property
def test_cli_buoys_plot_daily(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_plot_daily, [name, "sonde", observed_property])
    assert result.exit_code == 0

@by_station
def test_cli_buoys_firmware_template(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_firmware_template, [name, "--address", "1234", "--client", "test", "--file", "buoy.dld"])
    assert result.exit_code == 0


def test_cli_buoys_firmware_library():
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_firmware_library, ["--file", "lib.dld"])
    assert result.exit_code == 0
