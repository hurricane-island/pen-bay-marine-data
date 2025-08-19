# pylint: disable=too-many-locals
"""
Generate a custom firmware file from a template.
"""
from pathlib import Path
from hashlib import md5
import click

@click.group()
def buoys():
    """
    Command line interface for working with buoy data and firmware.
    """

@buoys.command()
@click.option("--name", required=True, help="Station name")
@click.option("--address", required=True, help="Pakbus address")
@click.option("--client", required=True, help="Client ID")
@click.option("--file", default="buoy.dld", help="Template file")
def template(name: str, address: str, client: str, file: str):
    """
    Fill in firmware template with options passed on
    the command line.
    """
    path = Path(__file__).parent.absolute()
    template_path = f"{path}/templates/{file}"
    with open(template_path, "r", encoding="utf-8") as fid:
        filedata = fid.read()

    for var, value in {
        "STATION_NAME": name,
        "PAKBUS_ADDRESS": address,
        "CLIENT_ID": client,
    }.items():
        slug = "$" + var
        filedata = filedata.replace(slug, value)

    encoded_data = filedata.encode("utf-8")
    hasher = md5()
    hasher.update(encoded_data)
    checksum = hasher.hexdigest()
    prefix = name.lower()
    firmware = f"{path}/firmware/{prefix}.{checksum}.dld"
    Path(firmware).parent.mkdir(parents=True, exist_ok=True)
    with open(firmware, "w", encoding="utf-8") as fid:
        fid.write(filedata)
