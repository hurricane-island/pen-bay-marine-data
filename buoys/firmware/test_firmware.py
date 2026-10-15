"""
Firmware CLI command tests.
"""

from buoys.firmware import buoys_firmware_template
from buoys.options import StationName
from buoys.test_buoys import by_station, runner


@by_station
def test_cli_buoys_firmware_template(name: StationName):
    """
    Expect files to be written to disk
    """
    result = runner.invoke(
        buoys_firmware_template,
        [name, "--address", "1234", "--client", "test", "--file", "buoy.dld"],
    )
    assert result.exit_code == 0
