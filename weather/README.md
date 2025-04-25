# Quickstart

Login to Balena CLI with `balena login` and use web authorization.

Commands should be run using `make` from the top-level project directory.

To build the Docker image for weather stations locally run `make weather`. You can take a look at the `makefile` to see the command that this runs. In short, it bundles the files in `/weather` into a container that will run on the data acquisition device.

The containers that will be part of the deployment are described in `docker-compose.yaml`, and include a Python container running WeeWx, and LoRa Basic Station.

You can view information about the device fleet with `balena fleet weather`, or a single device with `balena device <UUID>`. The UUID can be the short form or long form. You'll get this from the web dashboard.

To set new environment variables for the fleet:
`balena env set --fleet weather <VAR_NAME> <VAR_VALUE>`

Most of the variables needed for LoRaWAN and WeeWx are consistent across deployments. You'll need to update the coordinates, altitude, and station name for each deployment location.

To push new versions of the desired software to a fleet, `make deploy`.

This should result in two services being deployed: `weather` and `basicstation`.

If you go to the Balena Cloud logs for a specific device once these are running, you should see frequent data dumps. The Davis weather stations report about every 3 seconds, so the logs will be quite chatty. 

You'll need to get the Gateway EUI to register on The Things Network.

This can be done by opening a shell into `basicstation` and running the `gateway_eui` script. This will be used in TNN interface when creating the gateway. Choose to authenticate with LNS and download the access key. Copy this into the device level override of the `TC_KEY` environment variable.