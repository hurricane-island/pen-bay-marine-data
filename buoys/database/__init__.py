"""
Command line interface for working with buoy database.
"""

import sys
from typing import cast
from enum import StrEnum, auto
from pandas import DataFrame
from influxdb_client_3 import InfluxDBClient3
import requests
from click import ClickException, group, option, confirm, argument
from lib import (
    influx_host,
    influx_api_token,
)
from buoys.options import (
    StationName,
    TableName,
    station_name,
    data_table,
    filter_buoy_flat_files,
    read_single_campbell_logger_file,
)

def db_options(function):
    """
    Attach common options to source commands. When used as
    a decorator, the arguments and options will be supplied
    to the wrapped function in reverse order.
    """
    function = argument("bucket")(function)
    function = influx_api_token(function)
    function = influx_host(function)
    function = option(
        "--org-id",
        envvar="INFLUX_ORGID",
        required=True,
        help="InfluxDB Organization ID",
    )(function)
    return function


class DatabaseCommands(StrEnum):
    """
    Group and commands for interacting with the buoy database.
    """

    DATABASE = "db"
    DESCRIBE = auto()
    UPLOAD = auto()


class Metadata(StrEnum):
    """
    Metadata fields derived from first line of data file.
    """

    FEATURE = auto()
    DEVICE = auto()
    FIRMWARE = auto()
    SERIAL_NUMBER = "SerialNumber"
    DATALOGGER_OS_VERSION = "DataloggerOSVersion"
    AI1_OS_VERSION = "Ai1OSVersion"


@group(name=DatabaseCommands.DATABASE)
def database():
    """
    Commands that interact with the buoy database.
    """


@database.command(name="create")
@db_options
def buoys_db_create(bucket: str, host: str, token: str, org_id: str):
    """
    Create the buoy database.
    """
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    create_url = f"{host}/api/v2/buckets"
    payload = {
        "orgID": org_id,
        "name": bucket,
        "retentionRules": [{"type": "expire", "everySeconds": 0}],
    }
    create_response = requests.post(
        create_url, headers=headers, json=payload, timeout=10
    )
    if create_response.status_code != 201:
        raise ClickException(create_response.text)


@database.command(name=DatabaseCommands.UPLOAD)
@station_name
@data_table
@db_options
def buoys_db_upload(
    name: StationName,
    table: TableName,
    bucket: str,
    host: str,
    token: str,
    org_id: str
):
    """
    Upload buoy data to the database.
    """
    files = list(filter_buoy_flat_files(name, table))
    client = InfluxDBClient3(host=host, database=bucket, token=token, org=org_id)
    print(
        f"Uploading files for station '{name}' and table '{table}' to bucket '{bucket}'"
    )
    for each in files:
        df = read_single_campbell_logger_file(each)
        df.columns = [key[0] for key in df.columns]
        df.index.name = "index"
        with open(each, "r", encoding="utf-8") as fid:
            metadata = [each.strip('"') for each in fid.readline().strip().split(",")]
        logger_table = metadata[7]
        if logger_table != table:
            print(metadata)
            raise ValueError(
                f"Logger table '{logger_table}' does not match the expected table '{table}'"
            )
        df.insert(column=Metadata.FEATURE, value=metadata[1].lower(), loc=0)
        df.insert(column=Metadata.DEVICE, value=metadata[4], loc=3)
        df[Metadata.FIRMWARE] = metadata[5]
        if Metadata.SERIAL_NUMBER not in df.columns:
            df[Metadata.SERIAL_NUMBER] = metadata[3]
        client.write_dataframe(
            df.reset_index(),
            measurement=table,
            timestamp_column="index",
            tags=list(Metadata),
        )


@database.command(DatabaseCommands.DESCRIBE)
@station_name
@data_table
@db_options
def buoys_db_describe(
    name: StationName, table: TableName, bucket: str, host: str, token: str, org_id: str
):
    """
    Read all variables in a measurement (table) back from the
    influx database.
    """
    time = "time"
    count = 10
    client = InfluxDBClient3(host=host, database=bucket, token=token, org=org_id)
    print(f"Describing the first {count} rows of table '{table}' in bucket '{bucket}'")
    result = client.query(
        f"SELECT * FROM '{table}' WHERE {Metadata.FEATURE}='{name.value.lower()}' ORDER BY {time} LIMIT {count}",
        mode="pandas",
    )
    read_back = cast(DataFrame, result)
    print(read_back.head())


@database.command(name="delete")
@db_options
def buoys_db_delete(bucket: str, host: str, token: str, org_id: str):
    """
    Delete the InfluxDB bucket.
    """
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    find_url = f"{host}/api/v2/buckets?orgID={org_id}&name={bucket}"
    response = requests.get(find_url, headers=headers, timeout=5)
    if response.status_code != 200 or not response.json().get("buckets"):
        print(f"Error or bucket not found: {response.text}")
        sys.exit()
    bucket_id = response.json()["buckets"][0]["id"]
    if not confirm(
        f"Are you sure you want to delete the bucket '{bucket_id}'?", default=True
    ):
        sys.exit()
    delete_url = f"{host}/api/v2/buckets/{bucket_id}"
    delete_response = requests.delete(delete_url, headers=headers, timeout=5)
    if delete_response.status_code != 204:
        print(f"Failed to delete bucket: {delete_response.text}")
