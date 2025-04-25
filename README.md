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