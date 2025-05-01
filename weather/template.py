"""
Run inside the docker container on startup to populate the conf file 
from the container environment. Replaces WeeWx installation procedure.
"""
TEMPLATE = "/root/weewx-data/weewx.template.conf"
CONFIG = '/root/weewx-data/weewx.conf'
if __name__ == "__main__":
    from os import getenv
    with open(TEMPLATE, 'r', encoding='utf-8') as file:
        filedata = file.read()

    variables = [
        'TEMPLATE_STATION_LOCATION',
        'TEMPLATE_STATION_LATITUDE',
        'TEMPLATE_STATION_LONGITUDE',
        'TEMPLATE_STATION_ALTITUDE',
        'INFLUX_API_TOKEN',
        'INFLUX_MEASUREMENT',
        'INFLUX_BUCKET',
        'INFLUX_SERVER_URL'
    ]
    for var in variables:
        slug = "$" + var
        filedata: str = filedata.replace(slug, getenv(var))

    with open(CONFIG, 'w', encoding='utf-8') as file:
        file.write(filedata)
