"""
LoRaWAN CLI commands.
"""

from enum import StrEnum, auto
from pathlib import Path
from uuid import uuid4
from typing import Optional
from random import uniform, randint
from datetime import datetime, timedelta, timezone
import json
import requests
from click import IntRange, group, option, echo, argument
from pandas import json_normalize, to_datetime


class SignalMetric(StrEnum):
    """Signal metrics to plot."""

    RSSI = auto()
    SNR = auto()


class LoraWANCommand(StrEnum):
    """LoRaWAN CLI commands."""

    SYNC = auto()
    TAIL = auto()
    MOCK = auto()
    SECRET = auto()


class Dimension(StrEnum):
    """Dimensions for plotting."""

    ALTITUDE = auto()
    LATITUDE = auto()
    LONGITUDE = auto()
    RSSI = auto()
    SNR = auto()
    SATS = auto()
    HDOP = auto()


FIGURES_DIR = Path(__file__).parent / "figures"
WORKER_URL = "https://ttn-to-influx.hurricane-island.workers.dev/"
APPLICATION_ID = "hurricane-test-app"
DEVICE_ID = "field-tester-hurricane-rak10701-p"


@group()
def lorawan():
    """LoRaWAN CLI commands."""


@lorawan.group()
def plot():
    """Plot CLI commands."""


@lorawan.group()
def device():
    """Device management"""


@lorawan.group()
def db():
    """Cloud database CLI commands."""


@lorawan.group()
def describe():
    """Describe LoRaWAN devices and messages."""


def parse_uplink_message(message: dict) -> dict:
    """
    Parse the uplink message from TTN API. This should be the same transformation
    that takes place in the Cloudflare Worker that writes to InfluxDB.
    """
    result = message.get("result", {})
    uplink = result.get("uplink_message", {})
    payload = uplink.get("decoded_payload", {})
    metadata = uplink.get("rx_metadata", [{}])[0]
    broker = metadata.pop("packet_broker")
    message_id = broker.get("message_id")
    del metadata["gateway_ids"]
    altitude = payload.pop("altitude", None)
    # latitude = payload.get("latitude")
    # longitude = payload.get("longitude")
    # corrected = to_altitude(latitude, longitude, altitude) if altitude is not None else None
    return {"id": message_id, "altitude": altitude, **payload, **metadata}


def ttn_device_url(subdomain: str, region: str, application_id: str, device_id: str):
    """Construct the URL for a TTN device."""
    domain = f"https://{subdomain}.{region}.cloud.thethings.industries"
    route = f"api/v3/as/applications/{application_id}/devices/{device_id}"
    return f"{domain}/{route}"


def fetch_uplink_messages(
    application_id: str,
    device_id: str,
    api_key: str,
    limit: int,
    timeout: int,
    subdomain: str,
    region: str,
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
) -> list[dict]:
    """
    Fetch uplink messages from TTN API.

    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    device_url = ttn_device_url(subdomain, region, application_id, device_id)
    url = f"{device_url}/packages/storage/uplink_message"
    url += f"?limit={limit}"
    if after is not None:
        url += f"&after={after.isoformat()}"
    if before is not None:
        url += f"&before={before.isoformat()}"
    result = requests.get(url, headers=headers, timeout=timeout)
    if result.status_code != 200:
        echo(f"Failed to retrieve data from TTN API: {result.status_code}")
        return []
    items = result.text.split("\n\n")
    # filter empty lines and load each message as JSON
    return list(map(json.loads, filter(None, items)))


def ttn_options(function):
    """
    Decorator to add common TTN options to a Click command. These are
    all required for API calls to TTN.
    """
    function = option(
        "--region", default="nam1", help="TTN region.", required=True
    )(function)
    function = option(
        "--subdomain", default="neracoos", help="TTN subdomain.", required=True
    )(function)
    function = option(
        "--application-id",
        default=APPLICATION_ID,
        help="TTN application ID.",
        required=True,
    )(function)
    function = option(
        "--device-id", default=DEVICE_ID, help="TTN device ID.", required=True
    )(function)
    function = option(
        "--api-key",
        envvar="TTN_API_KEY",
        help="TTN API key with write permissions on devices",
        required=True,
    )(function)
    function = option(
        "--timeout",
        default=5,
        type=IntRange(min=1, max=60),
        help="Timeout for HTTP requests in seconds.",
        required=True,
    )(function)
    return function


@device.command(name="uplink")
@ttn_options
def lorawan_device_uplink_decoder(
    application_id: str,
    device_id: str,
    api_key: str,
    region: str,
    subdomain: str,
    timeout: int,
):
    """
    Use HTTP API to send a new decoder, so that we can keep the code in git
    instead of manually uploading.

    Reference: https://www.thethingsindustries.com/docs/api/reference/http/routes/#asapplications{end_device.ids.application_ids.application_id}devices{end_device.ids.device_id}-put
    """
    if len(api_key) == 0:
        raise EnvironmentError("Things Network API key is not in environment")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    url = ttn_device_url(subdomain, region, application_id, device_id)
    filepath = (Path(__file__).parent / device_id).with_suffix(".js")
    if not filepath.exists():
        # This won't work once we have multiple of the same device
        raise FileNotFoundError("Decoder file name should be equal to device ID")
    with open(filepath, "r", encoding="utf-8") as fid:
        src_code = fid.read()

    response = requests.put(
        url,
        headers=headers,
        json={
            "end_device": {
                "ids": {
                    "application_ids": {"application_id": application_id},
                    "device_id": device_id,
                },
                "formatters": {
                    "up_formatter": "FORMATTER_JAVASCRIPT",
                    "up_formatter_parameter": src_code,
                },
            },
            "field_mask": {
                "paths": [
                    "formatters.up_formatter",
                    "formatters.up_formatter_parameter",
                ]
            },
        },
        timeout=timeout,
    )
    print(response.status_code, response.text)


@db.command(name=LoraWANCommand.TAIL)
@ttn_options
@option(
    "--limit",
    default=10,
    type=IntRange(min=1, max=1000),
    help="Number of latest uplink messages to retrieve.",
)
def lorawan_db_tail(**kwargs):
    """
    Display a table of signal metrics (RSSI, SNR) for the given device.
    """
    time = "time"
    messages = fetch_uplink_messages(**kwargs)
    data = map(parse_uplink_message, messages)
    df = json_normalize(list(data))
    df[time] = to_datetime(df[time]).dt.tz_convert("America/New_York")
    df.set_index(time, inplace=True)
    df = df[list(Dimension)]
    print(df)


@db.command(name=LoraWANCommand.SECRET)
def lorawan_db_secret():
    """
    Create a secret to add to TTN and Cloudflare Workers.
    """
    secret = uuid4().hex
    echo("Add this secret to your TTN Webhook and Cloudflare Worker:")
    echo(f"{secret}")


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
                    "sats": randint(4, 10),
                },
                "rx_metadata": [
                    {
                        "gateway_ids": {"gateway_id": "packetbroker"},
                        "packet_broker": {
                            "message_id": "test",
                        },
                        "time": now.replace(tzinfo=None).isoformat() + "Z",
                        "rssi": rssi,
                        "channel_rssi": rssi,
                        "snr": uniform(-12, 10),
                        "received_at": rx_time.replace(tzinfo=None).isoformat()
                        + "000Z",
                    }
                ],
            },
        }
    }
    return message


@db.command(name=LoraWANCommand.MOCK)
@argument("device_id", default="mock-device")
@option(
    "--secret",
    default="",
    envvar="WEBHOOK_SECRET",
    help="Webhook secret to use. If not provided, will use WEBHOOK_SECRET from environment.",
)
def lorawan_db_mock(device_id: str, secret: str):
    """
    Send a test message to the Cloudflare Worker that writes to InfluxDB.
    This is useful for testing the integration without sending real data from a device.
    """
    echo("Sending test message to Cloudflare Worker...")
    message = create_mock_message(device_id)
    headers = {"X-TTN-Secret": secret}
    response = requests.post(
        WORKER_URL, json=message["result"], headers=headers, timeout=10
    )
    if response.status_code == 204:
        echo("Test message sent successfully.")
    else:
        echo(f"Failed to send test message: {response.status_code}")
        echo(f"Response: {response.text}")


@db.command(name=LoraWANCommand.SYNC)
@ttn_options
@option(
    "--webhook-secret",
    envvar="WEBHOOK_SECRET",
    help="Webhook secret to use.",
    required=True,
)
@option(
    "--limit",
    default=100,
    type=IntRange(min=1, max=1000),
    help="Maximum number of uplink messages to fetch from TTN.",
)
def lorawan_db_sync(
    webhook_secret: str, timeout: int, **kwargs
):
    """
    Sync the latest uplink messages from TTN to InfluxDB via the Cloudflare Worker.
    This is useful for backfilling data that may have been missed by the webhook.
    Unless values/keys have changed, this should be idempotent and safe to run multiple times.
    """
    data = fetch_uplink_messages(timeout=timeout, **kwargs)
    echo(f"Syncing {len(data)} uplink messages from TTN to InfluxDB.")
    headers = {"X-TTN-Secret": webhook_secret}
    for message in data:
        response = requests.post(
            WORKER_URL, json=message["result"], headers=headers, timeout=timeout
        )
        if response.status_code != 204:
            echo(f"Failed to send message: {response.status_code}")
            echo(f"Response: {response.text}")
