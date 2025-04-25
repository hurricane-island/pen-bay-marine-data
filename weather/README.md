# Quickstart

Login to Balena CLI with `balena login` and use web authorization.

Commands should be run using `make` from the top-level project directory.

To build the Docker image for weather stations locally run `make weather`. You can take a look at the `makefile` to see the command that this runs. In short, it bundles the files in `/weather-stations` into a container that will run on the data acquisition device.

You can view information about the device fleet with `balena fleet weather`, or a single device with `balena device <UUID>`. The UUID can be the short form or long form. You'll get this from the web dashboard.

To push new versions of the desired software to a fleet, `make deploy`.

