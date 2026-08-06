"""
LoRaWAN CLI commands.
"""
from enum import Enum
from os import getenv
from pathlib import Path
from math import log2
from random import uniform, randint
from datetime import datetime, timedelta, timezone
import json
import requests
import click
from matplotlib.pyplot import subplots
from matplotlib.ticker import MaxNLocator
from pyproj import Transformer
from pandas import json_normalize, to_datetime
import cartopy.crs as ccrs
from cartopy.io.img_tiles import OSM


# Create a transformer from WGS84 3D Ellipsoidal to WGS84 + EGM96 Sea Level Altitude
# EPSG:4979 is Latitude/Longitude/Ellipsoidal height (3D)
# EPSG:5773 is EGM96 orthometric height (altitude above sea level)
transformer = Transformer.from_crs(
    "EPSG:4979", 
    "EPSG:4326+5773", 
    always_xy=True
)

FIGURES_DIR = Path(__file__).parent / "figures"

# CRS the GPS payload is reported in, used as the `transform` for data artists.
#
# Do NOT use ccrs.PlateCarree() here. In cartopy 0.25 it is defined as an
# *ellipsoidal* equidistant cylindrical projection (`+proj=eqc +ellps=WGS84
# +to_meter=111319.49`), so its y axis is meridional arc length rather than
# geodetic latitude. Transforming it to a spherical Web Mercator makes PROJ
# apply an ellipsoid-to-sphere datum shift, which offsets latitude by ~0.19deg
# (~34 km at 44N) and silently lands the map inland. ccrs.Geodetic() round-trips
# to EPSG:3857 exactly.
GEODETIC = ccrs.Geodetic()

# Natural Earth's finest shoreline is 1:10,000,000 (~1 km), which merges harbors
# into the land polygon. Field-tester tracks span hundreds of meters, so use a
# web-tiled basemap and adopt its conformal Web Mercator projection instead.
# Web Mercator keeps local shapes and bearings true; an equal-aspect PlateCarree
# axes would stretch longitude by 1/cos(latitude) (~1.39x at 44N).
# Tiles are cached in the repo (and gitignored) so repeat plots do not re-request
# them; OSM's tile policy also asks for a descriptive user agent.
BASEMAP = OSM(cache=Path(__file__).parent / ".tile-cache", user_agent="pen-bay-marine-data")

# Minimum map span, so a stationary track does not zoom in past the tile detail.
MIN_SPAN_DEG = 0.004


def tile_zoom(span_deg, target_px=1400, max_zoom=19):
    """Pick the tile zoom level that renders `span_deg` at about `target_px` wide."""
    zoom = int(log2(target_px * 360 / (256 * span_deg)))
    return max(1, min(max_zoom, zoom))


def padded_extent(longitude, latitude, fraction=0.25):
    """Bounding box around the track, padded and floored at `MIN_SPAN_DEG`."""
    lon_mid, lat_mid = (longitude.max() + longitude.min()) / 2, (latitude.max() + latitude.min()) / 2
    lon_span = max(longitude.max() - longitude.min(), MIN_SPAN_DEG) * (1 + 2 * fraction)
    lat_span = max(latitude.max() - latitude.min(), MIN_SPAN_DEG) * (1 + 2 * fraction)
    return [
        lon_mid - lon_span / 2,
        lon_mid + lon_span / 2,
        lat_mid - lat_span / 2,
        lat_mid + lat_span / 2,
    ], lon_span


def label_degrees(ax, extent, nbins=6):
    """Tick a projected axes in degrees.

    Neither of cartopy's built-in options works here: `set_xticks(crs=...)`
    rejects a Geodetic CRS as "non-rectangular", and gridliner labels
    (`gridlines(draw_labels=True)`) report a degenerate tight bbox that crops the
    saved figure down to the colorbar. So transform the ticks ourselves.
    """
    for axis, setter, (low, high), hemispheres in (
        (ax.xaxis, ax.set_xticks, extent[:2], "WE"),
        (ax.yaxis, ax.set_yticks, extent[2:], "SN"),
    ):
        degrees = [
            value
            for value in MaxNLocator(nbins=nbins).tick_values(low, high)
            if low <= value <= high
        ]
        # Longitude ticks vary along x only and latitude ticks along y only, so
        # the opposite coordinate is an arbitrary in-view value.
        projected = [
            ax.projection.transform_point(*point, GEODETIC)
            for point in (
                [(value, extent[2]) for value in degrees]
                if axis is ax.xaxis
                else [(extent[0], value) for value in degrees]
            )
        ]
        setter([xy[0] if axis is ax.xaxis else xy[1] for xy in projected])
        axis.set_ticklabels(
            [
                f"{abs(value):.3f}\N{DEGREE SIGN}{hemispheres[int(value >= 0)]}"
                for value in degrees
            ]
        )



@click.group()
def lorawan():
    """LoRaWAN CLI commands."""


@lorawan.group()
def plot():
    """Plot CLI commands."""


@lorawan.group()
def db():
    """Cloud database CLI commands."""

@lorawan.group()
def describe():
    """Describe LoRaWAN devices and messages."""


def to_altitude(lat, lon, ellipsoidal_height):
    """Convert ellipsoidal height to altitude above sea level."""
    lon, lat, altitude = transformer.transform(lon, lat, ellipsoidal_height)
    return altitude

def parse_uplink_message(data):
    """Parse the uplink message from TTN API."""
    message = json.loads(data)
    result = message.get("result", {})
    uplink = result.get("uplink_message", {})
    payload = uplink.get("decoded_payload", {})
    metadata = uplink.get("rx_metadata", [])[0]
    broker = metadata.pop("packet_broker")
    message_id = broker.get("message_id")
    del metadata["gateway_ids"]
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    altitude = payload.pop("altitude", None)
    corrected = to_altitude(latitude, longitude, altitude) if altitude is not None else None
    return  {
        "id": message_id,
        "altitude": corrected,
        **payload,
        **metadata
    }

class SignalMetric(Enum):
    """Signal metrics to plot."""
    RSSI = "rssi"
    SNR = "snr"


@plot.command()
@click.option("--zoom", type=int, default=None, help="Basemap tile zoom level. Defaults to auto.")
def signal(zoom):
    """Map signal strength."""
    click.echo("Mapping signal strength...")
    api_key = getenv("TTN_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    device_id = "field-tester-hurricane-rak10701-p"
    url = f"https://neracoos.nam1.cloud.thethings.industries/api/v3/as/applications/hurricane-test-app/devices/{device_id}/packages/storage/uplink_message"
    result = requests.get(url, headers=headers, timeout=10)
    if result.status_code != 200:
        click.echo(f"Failed to retrieve data from TTN API. Status code: {result.status_code}")
        return
    all_data = result.text.split("\n\n")
    # data = parse_uplink_message(all_data[0])  # Get the first event
    data = map(parse_uplink_message, filter(None, all_data))  # Get the first event
    df = json_normalize(data)
    df["time"] = to_datetime(df["time"]).dt.tz_convert("America/New_York")
    df.set_index("time", inplace=True)
    df = df[["latitude", "longitude", "altitude", "sats", "rssi", "snr"]]
    print(df)

    metric = SignalMetric.RSSI
    extent, lon_span = padded_extent(df["longitude"], df["latitude"])
    fig, ax = subplots(figsize=(10, 8), subplot_kw={"projection": BASEMAP.crs})
    ax.set_extent(extent, crs=GEODETIC)
    ax.add_image(BASEMAP, zoom if zoom is not None else tile_zoom(lon_span))
    points = ax.scatter(
        x=df["longitude"],
        y=df["latitude"],
        c=df[metric.value],
        cmap="spring",
        s=50,
        edgecolor="black",
        linewidth=0.3,
        transform=GEODETIC,
        zorder=3,
    )
    ax.gridlines(linewidth=0.3, color="gray", alpha=0.5)
    label_degrees(ax, extent)
    fig.colorbar(points, ax=ax, label=metric.name, shrink=0.8)
    filepath = FIGURES_DIR / f"signal_{metric.name.lower()}.png"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filepath, dpi=200, bbox_inches="tight")

@describe.command("tail")
@click.argument("application_id", default="hurricane-test-app")
@click.argument("device_id", default="field-tester-hurricane-rak10701-p")
def lorawan_describe_tail(application_id, device_id):
    """
    Describe the latest uplink message from the field-tester device.
    """
    click.echo("Retrieving latest uplink message from TTN API...")
    api_key = getenv("TTN_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    url = f"https://neracoos.nam1.cloud.thethings.industries/api/v3/as/applications/{application_id}/devices/{device_id}/packages/storage/uplink_message"
    result = requests.get(url, headers=headers, timeout=10)
    if result.status_code != 200:
        click.echo(f"Failed to retrieve data from TTN API. Status code: {result.status_code}")
        return
    all_data = result.text.split("\n\n")
    data = json.loads(all_data[0])  # Get the first event
    click.echo(json.dumps(data, indent=4))

@db.command(name="mock")
@click.argument("device_id", default="mock-device")
def lorawan_db_mock(device_id):
    """
    Send a test message to the Cloudflare Worker that writes to InfluxDB.
    This is useful for testing the integration without sending real data from a device.
    """
    click.echo("Sending test message to Cloudflare Worker...")
    now = datetime.now(timezone.utc)
    rx_time = now + timedelta(seconds=uniform(0, 5))
    rssi = uniform(-120, -30)
    message = {
        "result": {
            "end_device_ids": {
                "device_id": device_id,
            },
            "uplink_message": {
                "decoded_payload": {
                    "accuracy": uniform(1, 3),
                    "altitude": uniform(-50, 50),
                    "hdop": uniform(0, 2),
                    "latitude": 44.1039545,
                    "longitude": -69.1044722,
                    "sats": randint(4, 10)
                },
                "rx_metadata": [
                    {
                        "gateway_ids": {
                            "gateway_id": "packetbroker"
                        },
                        "packet_broker": {
                            "message_id": "test",
                        },
                        "time": now.replace(tzinfo=None).isoformat() + "Z",
                        "rssi": rssi,
                        "channel_rssi": rssi,
                        "snr": uniform(-12, 10),
                        "received_at": rx_time.replace(tzinfo=None).isoformat() + "000Z"
                    }
                ],
            }
        }
    }
    # print(json.dumps(message, indent=4))
    response = requests.post(
        "https://ttn-to-influx.nkeeney.workers.dev/",
        json=message["result"],
        timeout=10
    )
    if response.status_code == 200:
        click.echo("Test message sent successfully.")
    else:
        click.echo(f"Failed to send test message. Status code: {response.status_code}")
        click.echo(f"Response: {response.text}")