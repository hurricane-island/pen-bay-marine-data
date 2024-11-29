# Run inside the docker container on startup to populate the conf file from the container environment
import os;
with open('/root/weewx-data/weewx.template.conf', 'r') as file:
  filedata = file.read()
filedata = filedata.replace('$TEMPLATE_STATION_LOCATION', os.getenv('TEMPLATE_STATION_LOCATION'))
filedata = filedata.replace('$TEMPLATE_STATION_LATITUDE', os.getenv('TEMPLATE_STATION_LATITUDE'))
filedata = filedata.replace('$TEMPLATE_STATION_LONGITUDE', os.getenv('TEMPLATE_STATION_LONGITUDE'))
filedata = filedata.replace('$TEMPLATE_STATION_ALTITUDE', os.getenv('TEMPLATE_STATION_ALTITUDE'))
with open('/root/weewx-data/weewx.conf', 'w') as file:
  file.write(filedata)