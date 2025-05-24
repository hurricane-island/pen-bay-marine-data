# pen-bay-marine-data

## Overview
Code and data associated with the Pen Bay Marine Data project. This includes documentation and methods for both controlling the loggers, and accessing the data published to Xylem Cloud.

Mooring simulation configurations are in `cable/`.

Code related to accessing and processing data is packaged in `client/`. 

Static data files are in `data/`, these are likely to be CSV, JSON, or GeoJSON.

QARTOD implementation is in `ioos_qc/`.

Campbell Scientific logger programs are in `logger-programs/`.

LoRaWAN specific configuration is in `lorawan/`.

And weather station management using WeeWx is in `weewx/`.

This repository uses `make` to orchestrate the build steps found in `makefile`, and `direnv` to manage a local environment found in `.envrc`. Building and deploying services to edge devices is managed with Docker and Balena.

The OpenAPI specification for the Xylem cloud data access API is in `xcloud-openapi.yaml`. You can test access by running `make test-client`.

Please see the Wiki for implementation rationale and research.

## Getting Help

How-to and troubleshooting information is in the project Wiki. Non-public information is kept in the the Google Drive project folder.

## Required Software

You will need a variety of software tools installed and configured to work on this project. Some tasks also require access to cloud software-as-a-service, that may not be available to the general public. 

### Development

Most of the required software will work on Windows or MacOS. Some vendor software will only work on Windows, but may be able to run using on MacOS using Crossover.

For developers working on the project we recommend setting up:

- Docker
- Git
- VSCode
- Warp
- NodeJS
- Balena CLI
- RStudio
- Make
- Crossover

You may also want to be familiar with:
- WeeWx
- WHOI Cable

Additionally, you may need access to accounts for:

- The Things Network
- Balena Cloud
- Github
- Hydrosphere / Xylem Cloud
- Influx DB

## Weather Stations

Login to Balena CLI with `balena login` and use web authorization.

To build the Docker image locally run `make weather`. In short, it bundles the files in this directory into a container that will run on the data acquisition device. The deployment is described in `docker-compose.yaml`, and includes a container running WeeWx, and one with LoRa Basic Station.

You can view information about the device fleet with `balena fleet weather`, or a single device with `balena device <UUID>`. The UUID can be the short form or long form. You'd get this from the web dashboard.

To set new environment variables for the fleet:
`balena env set --fleet weather <VAR_NAME> <VAR_VALUE>`

Most of the variables needed for LoRaWAN and WeeWx are consistent across deployments. You'll have to update the coordinates, altitude, and station name for each deployment location. As well as the Influx database to write to.

To push new versions of to a fleet, use `make deploy`. This will produce two services: `weather` and `basicstation`.

If you look at Balena Cloud logs for a specific device, you should see frequent data reports, about every 3 seconds for a Davis Vantage.

### Local queries

The container has sqlite installed to be able query the database locally.

Run `sqlite3 root/weewx-data/archive/weewx.sdb -readonly` to enter readonly mode. Entering `.tables` will list the tables available to query. The query `PRAGMA table_info(<TABLE_NAME>);` will show information about the table columns. WeeWx has a wide `archive` table, and tables for each parameter.

You can count the number of records with `SELECT COUNT(1) FROM archive;`

### Log level

Set `debug=2` in configuration file.

Rebuild and deploy to the desired fleet.

https://docs.balena.io/learn/manage/device-logs/

### Delete volume

Use the `Purge Data` option in the Actions menu for the device or fleet. This is needed to get rid of the sqlite db. 

## LoRaWAN

You'll need to get the Gateway EUI to register on The Things Network.

This can be done by opening a shell into `basicstation` and running the `gateway_eui` script. This will be used in TTN interface when creating the gateway. Choose to authenticate with LNS and download the access key. Copy this into the device level override of the `TC_KEY` environment variable.


## Use of Generative AI

Some code in this repository was suggested or written by Generative AI products including Github Copilot and Warp Terminal.