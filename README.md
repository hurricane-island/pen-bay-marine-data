# pen-bay-marine-data
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