"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
import pytest
from pathlib import Path
from click.testing import CliRunner
from profiles import profiles_plot_single, profiles_plot_transect, Dimension

DATA_DIR = Path(__file__).parent / "data"

runner = CliRunner()

all_files = [f.stem for f in DATA_DIR.glob("*.csv")]
transects = ["260827"]
dimensions = [each.name for each in [
    Dimension.TEMPERATURE,
    Dimension.SALINITY,
    Dimension.DO_SATURATION,
    Dimension.DO_CONCENTRATION,
    Dimension.DENSITY
]]


@pytest.mark.parametrize("filename", all_files)
@pytest.mark.parametrize("dim", dimensions)
def test_cli_profiles_plot_single(filename: str, dim: str):
    """
    Expect command line output when plotting a single profile for the given filename.
    """
    result = runner.invoke(profiles_plot_single, [
        filename,
        "--dim", dim
    ])
    assert result.exit_code == 0

@pytest.mark.parametrize("transect_date", transects)
@pytest.mark.parametrize("dim", dimensions)
def test_cli_profiles_plot_transect(transect_date: str, dim: str):
    """
    Expect command line output when plotting a single profile for the given filename.
    """
    result = runner.invoke(profiles_plot_transect, [
        transect_date,
        "--dim", dim,
        "--levels", 100
    ])
    assert result.exit_code == 0
