"""
Commands for working with buoy firmware.
"""

from enum import StrEnum, auto
from pathlib import Path
from hashlib import md5
from typing import Optional
from click import group, option, FloatRange
from buoys.options import FEATURES_OF_INTEREST, station_name, StationName

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
@option("--address", required=True, help="Pakbus address, specific to hardware items.")
@option("--client", required=True, help="Client ID, specific to geographic location")
@option("--file", default="buoy.dld", help="Template file")
@option(
    "--latitude",
    required=False,
    type=FloatRange(-90.0, 90.0),
    help="Latitude of the station",
    default=None,
)
@option(
    "--longitude",
    required=False,
    type=FloatRange(-180.0, 180.0),
    help="Longitude of the station",
    default=None,
)
def buoys_firmware_template(
    name: StationName,
    address: str,
    client: str,
    file: str,
    latitude: Optional[float],
    longitude: Optional[float],
):
    """
    Fill in a firmware template with options for a specific buoy station.
    Latitude and longitude are automatically filled based on expected
    station coordinates if not provided.
    """
    with open(TEMPLATE_DIR / file, "r", encoding="utf-8") as fid:
        filedata = fid.read()
    coordinates = FEATURES_OF_INTEREST[name].feature.coordinates
    for var, value in {
        "STATION_NAME": name,
        "PAKBUS_ADDRESS": address,
        "CLIENT_ID": client,
        "LATITUDE": latitude or coordinates.latitude,
        "LONGITUDE": longitude or coordinates.longitude,
    }.items():
        slug = "$" + var
        filedata = filedata.replace(slug, f"{value}")

    prefix = name.lower()
    filename = FIRMWARE_DIR / f"{prefix}.{checksum(filedata)}.dld"
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as fid:
        fid.write(filedata)
