"""
Command line interface for working with buoy firmware.
"""

from enum import Enum
from pathlib import Path
from hashlib import md5
from click import group, option, echo
from buoys import buoys, station_name, StationName

FIRMWARE_DIR = Path(__file__).parent / "programs"
TEMPLATE_DIR = Path(__file__).parent / "templates"


class FirmwareCommands(Enum):
    """
    Enum for firmware commands.
    """

    FIRMWARE = "firmware"
    TEMPLATE = "template"
    LIBRARY = "lib"


@group(name=FirmwareCommands.FIRMWARE.value)
def firmware():
    """
    Command line interface for working with buoy data and firmware.
    """


buoys.add_command(firmware)


def checksum(contents: str) -> str:
    """
    Generate a checksum for a file based on its contents.
    This can be used to create unique filenames for firmware templates.
    """
    encoded_data = contents.encode("utf-8")
    hasher = md5()
    hasher.update(encoded_data)
    return hasher.hexdigest()


@firmware.command(name=FirmwareCommands.TEMPLATE.value)
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
        "STATION_NAME": name.value,
        "PAKBUS_ADDRESS": address,
        "CLIENT_ID": client,
        "LATITUDE": latitude,
        "LONGITUDE": longitude,
    }.items():
        slug = "$" + var
        filedata = filedata.replace(slug, value)

    prefix = name.value.lower()
    filename = FIRMWARE_DIR / f"{prefix}.{checksum(filedata)}.dld"
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as fid:
        fid.write(filedata)


@firmware.command(name=FirmwareCommands.LIBRARY.value)
@option("--file", default="lib.dld", help="Template file")
def buoys_firmware_library(file: str):
    """
    Fill in firmware template with options passed on
    the command line.
    """
    with open(TEMPLATE_DIR / file, "r", encoding="utf-8") as fid:
        filedata = fid.read()
    filename = FIRMWARE_DIR / f"lib.{checksum(filedata)}.dld"
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "w", encoding="utf-8") as fid:
        fid.write(filedata)


@firmware.command(name="mock")
@station_name
def buoys_firmware_mock(name: StationName):
    """
    Generate a mock message from a buoy logger for testing cloud
    integrations, including databases, location alerts, and missing
    data detection.
    """
    # comma separate list, with each up to 26 characters
    head = f"SL({name.value.lower()})\r"
    names = "SN=ExternalTemp,SpConductivity_us,Pressure_abs,Chlorophyll_RFU,BGA_PE_RFU,BatteryVoltage,InternalHumidity,Salinity,Latitude,Longitude"
    values = (
        "D=08/11/26,17:15:00,13.42,41200,10.15,2.87,0.41,13.06,38,44.04203,-68.89106\r"
    )
    tail = "DIS\r"
    echo(head + names + values + tail)
