# pen-bay-marine-data
Code and data associated with the Pen Bay Marine Data project. This includes documentation and methods for both controlling the loggers, and accessing the data published to Xylem Cloud.

This repository uses `make` to orchestrate the build steps found in `makefile`, and `direnv` to manage a local environment found in `.envrc`.

The environment file is local, to prevent cross-organization sharing of API and access keys.

The OpenAPI specification for the Xylem cloud data access API is in `xcloud-openapi.yaml`.

Data files are in `data/`, these are likely to be CSV, JSON, or GeoJSON.

Campbell Scientific logger programs are in `logger-programs/`.

