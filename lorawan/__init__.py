"""
LoRaWAN CLI commands.
"""
from enum import Enum
from os import getenv
from pathlib import Path
from uuid import uuid4
from typing import Optional
from random import uniform, randint
from datetime import datetime, timedelta, timezone
import json
import requests
import click
from pyproj import Transformer
from pandas import json_normalize, to_datetime


class SignalMetric(Enum):
    """Signal metrics to plot."""
    RSSI = "rssi"
    SNR = "snr"


class LoraWANCommand(Enum):
    """LoRaWAN CLI commands."""
    SYNC = "sync"
    TAIL = "tail"
    MOCK = "mock"
    SECRET = "secret"
    SIGNAL = "signal"

# Create a transformer from WGS84 3D Ellipsoidal to WGS84 + EGM96 Sea Level Altitude
# EPSG:4979 is Latitude/Longitude/Ellipsoidal height (3D)
# EPSG:5773 is EGM96 orthometric height (altitude above sea level)
transformer = Transformer.from_crs(
    "EPSG:4979", 
    "EPSG:4326+5773", 
    always_xy=True
)

FIGURES_DIR = Path(__file__).parent / "figures"
WORKER_URL = "https://ttn-to-influx.hurricane-island.workers.dev/"
APPLICATION_ID = "hurricane-test-app"
DEVICE_ID = "field-tester-hurricane-rak10701-p"


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

def parse_uplink_message(message: dict) -> dict:
    """
    Parse the uplink message from TTN API. This should be the same transformation
    that takes place in the Cloudflare Worker that writes to InfluxDB.
    """
    result = message.get("result", {})
    uplink = result.get("uplink_message", {})
    payload = uplink.get("decoded_payload", {})
    metadata = uplink.get("rx_metadata", [])[0]
    broker = metadata.pop("packet_broker")
    message_id = broker.get("message_id")
    del metadata["gateway_ids"]
    altitude = payload.pop("altitude", None)
    # latitude = payload.get("latitude")
    # longitude = payload.get("longitude")
    # corrected = to_altitude(latitude, longitude, altitude) if altitude is not None else None
    return  {
        "id": message_id,
        "altitude": altitude,
        **payload,
        **metadata
    }


def fetch_uplink_messages(
    application_id: str,
    device_id: str,
    subdomain: str = "neracoos",
    region: str = "nam1",
    limit: Optional[int] = None
) -> list[dict]:
    """
    Fetch uplink messages from TTN API.
    """
    
    api_key = getenv("TTN_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    url = f"https://{subdomain}.{region}.cloud.thethings.industries/api/v3/as/applications/{application_id}/devices/{device_id}/packages/storage/uplink_message"
    if limit is not None:
        url += f"?limit={limit}"
    result = requests.get(url, headers=headers, timeout=10)
    if result.status_code != 200:
        click.echo(f"Failed to retrieve data from TTN API: {result.status_code}")
        return []
    items = result.text.split("\n\n")
    return list(map(json.loads, filter(None, items)))

@describe.command(name=LoraWANCommand.SIGNAL.value)
@click.option("--application-id", default=APPLICATION_ID, help="TTN application ID.")
@click.option("--device-id", default=DEVICE_ID, help="TTN device ID.")
def signal(application_id: str, device_id: str):
    """
    Display a table of signal metrics (RSSI, SNR) for the given device.
    The data is retrieved from the TTN API and displayed in a pandas DataFrame.
    """
    data = list(map(parse_uplink_message, fetch_uplink_messages(application_id, device_id)))
    df = json_normalize(data)
    df["time"] = to_datetime(df["time"]).dt.tz_convert("America/New_York")
    df.set_index("time", inplace=True)
    df = df[["latitude", "longitude", "altitude", "sats", "rssi", "snr"]]
    print(df)

@describe.command(name=LoraWANCommand.TAIL.value)
@click.argument("application_id", default=APPLICATION_ID)
@click.argument("device_id", default=DEVICE_ID)
def lorawan_describe_tail(application_id, device_id):
    """
    Describe the latest uplink message from the field-tester device.
    """
    click.echo("Retrieving latest uplink message from TTN API...")
    data = list(map(parse_uplink_message, fetch_uplink_messages(application_id, device_id, limit=1)))
    click.echo(json.dumps(data, indent=4))

@db.command(name=LoraWANCommand.SECRET.value)
def lorawan_db_secret():
    """
    Create a secret to add to TTN and Cloudflare Workers.
    """
    secret = uuid4().hex
    click.echo("Add this secret to your TTN Webhook and Cloudflare Worker:")
    click.echo(f"{secret}")

def create_mock_message(device_id: str):
    """
    Create a mock uplink message for testing. The top-level key is result, which matches the structure of the TTN API response. The message includes a decoded payload with random values for accuracy, altitude, hdop, latitude, longitude, and number of satellites. The rx_metadata includes a random RSSI value and a random SNR value. The time and received_at fields are set to the current time plus a random offset.
    """
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
    return message

@db.command(name=LoraWANCommand.MOCK.value)
@click.argument("device_id", default="mock-device")
@click.option("--secret", default=None, help="Webhook secret to use. If not provided, will use WEBHOOK_SECRET from environment.")
def lorawan_db_mock(device_id: str, secret: Optional[str]):
    """
    Send a test message to the Cloudflare Worker that writes to InfluxDB.
    This is useful for testing the integration without sending real data from a device.
    """
    click.echo("Sending test message to Cloudflare Worker...")
    message = create_mock_message(device_id)
    headers = {
        "X-TTN-Secret": secret or getenv("WEBHOOK_SECRET", "")
    }
    response = requests.post(
        WORKER_URL,
        json=message["result"],
        headers=headers,
        timeout=10
    )
    if response.status_code == 204:
        click.echo("Test message sent successfully.")
    else:
        click.echo(f"Failed to send test message: {response.status_code}")
        click.echo(f"Response: {response.text}")


@db.command(name=LoraWANCommand.SYNC.value)
@click.option("--application-id", default=APPLICATION_ID, help="TTN application ID.")
@click.option("--device-id", default=DEVICE_ID, help="TTN device ID.")
def lorawan_db_sync(application_id: str, device_id: str):
    """
    Sync the latest uplink messages from TTN to InfluxDB via the Cloudflare Worker.
    This is useful for backfilling data that may have been missed by the webhook.
    Unless values/keys have changed, this should be idempotent and safe to run multiple times.
    """
    data = fetch_uplink_messages(application_id, device_id)
    click.echo(f"Syncing {len(data)} (all) uplink messages from TTN to InfluxDB.")
    headers = {
        "X-TTN-Secret": getenv("WEBHOOK_SECRET", "")
    }
    for message in data:
        response = requests.post(
            WORKER_URL,
            json=message["result"],
            headers=headers,
            timeout=10
        )
        if response.status_code != 204:
            click.echo(f"Failed to send message: {response.status_code}")
            click.echo(f"Response: {response.text}")
