"""
Firmware CLI command tests.
"""

import pytest
from click.testing import CliRunner
from buoys.firmware import buoys_firmware_template

by_station = pytest.mark.parametrize("name", ["wynken", "blynken"])
runner = CliRunner()


@by_station
def test_cli_buoys_firmware_template(name):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(
        buoys_firmware_template,
        [name, "--address", "1234", "--client", "test", "--file", "buoy.dld"],
    )
    assert result.exit_code == 0
