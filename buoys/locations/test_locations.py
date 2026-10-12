"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
from click.testing import CliRunner
from buoys.locations import buoys_locations_plot_predict, buoys_locations_plot_map, buoys_locations_export_gpx
from buoys.options import StationName
from buoys.test_buoys import by_station

runner = CliRunner()

@by_station
def test_cli_buoys_locations_export_gpx(name):
    """
    Export GPX files for each buoy station.
    """
    result = runner.invoke(buoys_locations_export_gpx, [
        name,
        "--tail", "24",

    ])
    assert result.exit_code == 0


def test_cli_buoys_locations_plot_map():
    """
    Visualize mooring performance where there is a cable simulation.
    """
    result = runner.invoke(buoys_locations_plot_map,
        [
            StationName.WYNKEN,
            "--distance", "100",
            "--satellites", "10",
            "--start", "2024-01-01",
            "--end", "2026-12-31",
            "--cable"
        ])
    assert result.exit_code == 0

def test_cli_buoys_locations_plot_predict():
    """
    Visualize predicted watch circles where there is a cable simulation.
    """
    result = runner.invoke(buoys_locations_plot_predict, [
        StationName.WYNKEN
    ])
    assert result.exit_code == 0
