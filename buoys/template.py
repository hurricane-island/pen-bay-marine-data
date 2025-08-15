"""
Generate a custom firmware file from a template.
"""
from pathlib import Path
import click
import hashlib

@click.command()
@click.option('--name', required=True, help='Station name')
@click.option('--address', required=True, help='Pakbus address')
@click.option('--client', required=True, help='Client ID')
@click.option('--template', default="buoy.dld", help='Template file')
def template(name: str, address: str, client: str, template: str):
    path = Path(__file__).parent.absolute()
    template_path = f"{path}/templates/{template}"
    with open(template_path, 'r', encoding='utf-8') as file:
        filedata = file.read()

    for var, value in {
        'STATION_NAME': name,
        'PAKBUS_ADDRESS': address,
        'CLIENT_ID': client,
    }.items():
        slug = "$" + var
        filedata: str = filedata.replace(slug, value)

    encoded_data = filedata.encode('utf-8')
    hash = hashlib.md5()
    hash.update(encoded_data)
    checksum = hash.hexdigest()
    prefix = name.lower()
    firmware_path = f"{path}/firmware/{prefix}.{checksum}.dld"
    with open(firmware_path, 'w', encoding='utf-8') as file:
        file.write(filedata)

if __name__ == "__main__":
    template()
