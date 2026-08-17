"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
import pytest
from click.testing import CliRunner
from buoys import buoys_file_gpx, buoys_file_list, buoys_file_describe, buoys_file_export, buoys_plot_tail,TestTypes
from buoys.firmware import buoys_firmware_template, buoys_firmware_library

by_station = pytest.mark.parametrize("name", ["wynken", "blynken"])
by_observed_property = pytest.mark.parametrize("observed_property", ["sea_water_salinity", "sea_water_temperature", "sea_water_chlorophyll_rfu", "sea_water_phycoerythrin_rfu"])
by_qartod_test = pytest.mark.parametrize("qartod_test", [each.value for each in set(TestTypes) if each != TestTypes.GAP])
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


# Decorators are evaluated in reverse order
@by_qartod_test
@by_observed_property
@by_station
def test_cli_buoys_plot_tail(
    name: str,
    observed_property: str,
    qartod_test: str
):
    """
    Expect files to be written to disk
    """
    args = [
        name,
        "sonde",
        observed_property,
        "--days", "1000",
        "-q", "qartod.yaml",
        "-q", f"{name}.yaml",
        "--test", qartod_test,
        "--scale"
    ]
    result = runner.invoke(buoys_plot_tail, args)
    assert result.exit_code == 0

example_style_commands = [
    "--scale",
    "--figsize", 9.0, 4.5,
]

@by_station
def test_cli_buoys_plot_tail_examples_temperature_raw(
    name: str
):
    """
    Expect files to be written to disk
    """
    args = [
        name,
        "sonde",
        "sea_water_temperature",
        "--days", "1000",
        "-q", "empty.yaml",
        "--test", "rollup",
        *example_style_commands
    ]
    result = runner.invoke(buoys_plot_tail, args)
    assert result.exit_code == 0

@by_station
@by_qartod_test
def test_cli_buoys_plot_tail_examples_temperature(
    name: str,
    qartod_test: str
):
    """
    Expect files to be written to disk
    """
    args = [
        name,
        "sonde",
        "sea_water_temperature",
        "--days", "1000",
        "-q", "qartod.yaml",
        "-q", f"{name}.yaml",
        "--test", qartod_test,
        *example_style_commands
    ]
    result = runner.invoke(buoys_plot_tail, args)
    assert result.exit_code == 0

@by_station
@pytest.mark.parametrize("observed_property", ["sea_water_salinity", "sea_water_chlorophyll_rfu"])
def test_cli_buoys_plot_tail_examples_studies_raw(
    name: str,
    observed_property: str
):
    """
    Expect files to be written to disk
    """
    args = [
        name,
        "sonde",
        observed_property,
        "--end", "2026-08-16",
        "--days", "180",
        "-q", "empty.yaml",
        *example_style_commands
    ]
    result = runner.invoke(buoys_plot_tail, args)
    assert result.exit_code == 0

@by_qartod_test
@by_station
@pytest.mark.parametrize("observed_property", ["sea_water_salinity", "sea_water_chlorophyll_rfu"])
def test_cli_buoys_plot_tail_examples_studies(
    name: str,
    qartod_test: str,
    observed_property: str
):
    """
    Expect files to be written to disk
    """
    args = [
        name,
        "sonde",
        observed_property,
        "--end", "2026-08-16",
        "--days", "180",
        "-q", "qartod.yaml",
        "-q", f"{name}.yaml",
        "--test", qartod_test,
        "--no-scale",
        "--figsize", 9.0, 4.5,
    ]
    result = runner.invoke(buoys_plot_tail, args)
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
