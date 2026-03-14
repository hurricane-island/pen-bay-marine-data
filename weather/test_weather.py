"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or
tests will fail due to a system exit event.
"""

import pytest
from click.testing import CliRunner
from . import (
    weather_db_describe,
    weather_file_describe,
    weather_file_export,
    weather_plot_daily,
    weather_plot_tail,
    weather_describe_series,
)

runner = CliRunner()
by_station = pytest.mark.parametrize("name", ["apprenticeshop"])
by_observed_property = pytest.mark.parametrize(
    "observed_property",
    [
        "air_temperature",
        "wind_speed",
        "wind_speed_of_gust",
        "air_pressure",
        "relative_humidity",
    ],
)


@by_station
def test_cli_weather_file_describe(name):
    """
    Expect command line output
    """
    result = runner.invoke(weather_file_describe, [name])
    assert result.exit_code == 0


@by_station
def test_cli_weather_file_export(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(weather_file_export, [name])
    assert result.exit_code == 0


@by_station
@by_observed_property
def test_cli_weather_plot_tail(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(weather_plot_tail, [name, observed_property])
    assert result.exit_code == 0


@by_station
@by_observed_property
def test_cli_weather_describe(name, observed_property):
    """
    Expect command line output. Host, measurement, and API token are
    picked up from the environment.
    """
    # database picked up from envvar
    result = runner.invoke(weather_describe_series, [name, observed_property])
    assert result.exit_code == 0


@by_station
@by_observed_property
def test_cli_weather_plot_daily(name, observed_property):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(weather_plot_daily, [name, observed_property])
    assert result.exit_code == 0


def test_cli_weather_db_describe():
    """
    Expect command line output. Host, measurement, and API token are
    picked up from the environment.
    """
    result = runner.invoke(weather_db_describe, [])
    assert result.exit_code == 0
