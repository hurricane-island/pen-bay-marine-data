"""
Commands for working with buoy firmware.
"""

from enum import StrEnum, auto
from pathlib import Path
from hashlib import md5
from click import group, option
from buoys.options import station_name, StationName

FIRMWARE_DIR = Path(__file__).parent / "programs"
TEMPLATE_DIR = Path(__file__).parent / "templates"


class FirmwareCommands(StrEnum):
    """
    Enum for firmware commands.
    """

    FIRMWARE = auto()
    TEMPLATE = auto()


def checksum(contents: str) -> str:
    """
    Generate a checksum for a file based on its contents.
    This can be used to create unique filenames for firmware templates.
    """
    encoded_data = contents.encode("utf-8")
    hasher = md5()
    hasher.update(encoded_data)
    return hasher.hexdigest()


@group(name=FirmwareCommands.FIRMWARE)
def firmware():
    """
    Create firmware programs from a template.
    """


@firmware.command(name=FirmwareCommands.TEMPLATE)
@station_name
@option("--address", required=True, help="Pakbus address")
@option("--client", required=True, help="Client ID")
@option("--file", default="buoy.dld", help="Template file")
@option("--latitude", required=True, help="Latitude")
@option("--longitude", required=True, help="Longitude")
def buoys_firmware_template(
    name: StationName,
    address: str,
    client: str,
    file: str,
    latitude: str,
    longitude: str,
):
    """
    Fill in firmware template with options passed on
    the command line.
    """
    with open(TEMPLATE_DIR / file, "r", encoding="utf-8") as fid:
        filedata = fid.read()

    for var, value in {
        "STATION_NAME": name,
        "PAKBUS_ADDRESS": address,
        "CLIENT_ID": client,
        "LATITUDE": latitude,
        "LONGITUDE": longitude,
    }.items():
        slug = "$" + var
        filedata = filedata.replace(slug, value)

    prefix = name.lower()
    filename = FIRMWARE_DIR / f"{prefix}.{checksum(filedata)}.dld"
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as fid:
        fid.write(filedata)
