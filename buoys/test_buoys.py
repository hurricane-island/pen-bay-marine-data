"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
import pytest
from click.testing import CliRunner
from . import buoy_file_gpx, buoy_file_list, buoy_file_describe, buoy_file_export, buoy_plot_daily, buoy_plot_tail, buoys_firmware_library, buoys_firmware_template

by_station = pytest.mark.parametrize("name", ["wynken", "blynken"])
by_observed_property = pytest.mark.parametrize("observed_property", ["sea_water_salinity", "sea_water_temperature"])
runner = CliRunner()

def test_buoy_file_list():
    """
    List available stations
    """
    result = runner.invoke(buoy_file_list)
    assert result.exit_code == 0
    assert "Wynken" in result.output

@by_station
@pytest.mark.parametrize("table", ["sonde", "diagnostic"])
def test_buoy_file_describe(name, table):
    """
    Expect command line output
    """
    result = runner.invoke(buoy_file_describe, [name, table])
    assert result.exit_code == 0

@by_station
@pytest.mark.parametrize("table", ["sonde", "diagnostic"])
def test_buoy_file_export(name, table):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoy_file_export, [name, table])
    assert result.exit_code == 0

@by_station
def test_buoy_file_gpx(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoy_file_gpx, [name])
    assert result.exit_code == 0

@by_station
@by_observed_property
def test_buoy_plot_tail(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoy_plot_tail, [name, "sonde", observed_property])
    assert result.exit_code == 0

@by_station
@by_observed_property
def test_buoys_plot_daily(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoy_plot_daily, [name, "sonde", observed_property])
    assert result.exit_code == 0

@by_station
def test_buoy_firmware_template(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_firmware_template, [name, "--address", "1234", "--client", "test", "--file", "buoy.dld"])
    assert result.exit_code == 0


def test_buoy_firmware_library():
    """
    Expect files to be written to disk
    """
    result = runner.invoke(buoys_firmware_library, ["--file", "lib.dld"])
    assert result.exit_code == 0
