"""
Test the CLI commands.

Decorated commands need to be run with `standalone_mode=False`, or 
tests will fail due to a system exit event.
"""
import pytest
from click.testing import CliRunner
from profiles import profiles, plot, profiles_plot
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

runner = CliRunner()

all_files = [f.stem for f in DATA_DIR.glob("*.csv")]


@pytest.mark.parametrize("filename", all_files)
def test_cli_profiles_plot(filename: str):
    """
    Expect command line output when plotting a single profile for the given filename.
    """
    result = runner.invoke(profiles_plot, [filename])
    assert result.exit_code == 0
