"""
Command line interface for working with buoy database.
"""

from pathlib import Path
from typing import cast
from enum import StrEnum, auto
from pandas import DataFrame
from influxdb_client_3 import InfluxDBClient3
from requests import get, delete
from click import ClickException, echo, group, option, confirm, argument, IntRange
from lib import (
    influx_host,
    influx_api_token,
)
from lib.db import create_bucket
from buoys.options import (
    StationName,
    TableName,
    station_name,
    data_table,
    read_single_campbell_logger_file,
)


def db_options(function):
    """
    Attach common options to source commands. When used as
    a decorator, the arguments and options will be supplied
    to the wrapped function in reverse order.
    """
    function = argument("database")(function)
    function = influx_api_token(function)
    function = influx_host(function)
    function = option(
        "--org",
        envvar="INFLUX_ORGID",
        required=True,
        help="InfluxDB Organization ID",
    )(function)
    return function


class Source(StrEnum):
    """
    To help with determining the source format of each row in the database.
    """

    TOA5 = auto()
    CSIJSON = auto()


class DatabaseCommands(StrEnum):
    """
    Group and commands for interacting with the buoy database.
    """

    DATABASE = "db"
    DESCRIBE = auto()
    UPLOAD = auto()
    DELETE = auto()
    CREATE = auto()
    DIFF = auto()


class Tags(StrEnum):
    """
    Metadata fields derived from first line of data file.
    """
    # Tag constants
    STATION_NAME = auto()
    TABLE_NAME = auto()
    MODEL = auto()
    SERIAL_NO = auto()
    OS_VERSION = auto()
    PROG_NAME = auto()
    SOURCE = auto()
    # Tag columns
    DATALOGGER_OS_VERSION = "DataloggerOSVersion"
    AI1_OS_VERSION = "Ai1OSVersion"
    SERIAL_NUMBER = "SerialNumber"


@group(name=DatabaseCommands.DATABASE)
def db():
    """
    Commands that interact with the buoy database.
    """


@db.command(name=DatabaseCommands.CREATE)
@db_options
@option("--timeout", default=10, help="Timeout for the create request in seconds")
@option("--retention", default=0, help="Retention period for the bucket in seconds")
def buoys_db_create(**kwargs):
    """
    Create a new Influx DB database.
    """
    create_response = create_bucket(**kwargs)
    if create_response.status_code != 201:
        raise ClickException(create_response.text)


def parse_environment(filepath: Path):
    """
    Parse the environment variables for InfluxDB connection.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File '{filepath}' does not exist.")
    with open(filepath, "r", encoding="utf-8") as fid:
        metadata_line = fid.readline().strip()
        metadata = [item.strip('"') for item in metadata_line.split(",")]
    return metadata


@db.command(name=DatabaseCommands.UPLOAD)
@argument("filename")
@db_options
def buoys_db_upload(filename: str, **kwargs):
    """
    Upload a single CSV file to database using the Influx client.
    """
    filepath = Path(filename)
    [
        source,  # file format, not in CSIJSON payload
        _station_name,
        model,
        serial_no,
        os_version,
        prog_name,
        _,  # signature, not in CSIJSON payload
        table_name,
    ] = parse_environment(filepath)
    if source != Source.TOA5:
        raise ValueError(f"Unsupported file format '{source}'")
    if table_name not in filename:
        raise ValueError(f"Table '{table_name}' does not match filename '{filename}'")
    if _station_name not in filename:
        raise ValueError(f"Station '{_station_name}' does not match filename '{filename}'")

    index = "index"  # can't use "time" as name of index col
    df = read_single_campbell_logger_file(filepath)
    df.columns = [key[0] for key in df.columns]
    df.index.name = index

    df[Tags.SOURCE] = source
    df[Tags.STATION_NAME] = _station_name.lower()  # normalize station name
    df[Tags.MODEL] = model
    df[Tags.SERIAL_NO] = serial_no
    df[Tags.OS_VERSION] = os_version
    df[Tags.PROG_NAME] = prog_name
    # don't need signature, table_name

    InfluxDBClient3(**kwargs).write_dataframe(
        df.reset_index(),
        measurement=table_name,
        timestamp_column=index,
        tags=list(Tags),
    )


@db.command(DatabaseCommands.DIFF)
@argument("filename")
@db_options
def buoys_db_diff(filename: str, **kwargs):
    """
    Determine whether any of the records in the CSV
    file are missing from the cloud database.
    """
    time = "time"
    client = InfluxDBClient3(**kwargs)
    filepath = Path(filename)
    metadata = parse_environment(filepath)
    query = f"""
        SELECT * FROM "{metadata[7]}"
        WHERE "{Tags.PROG_NAME}" == '{metadata[5]}'
            AND "{Tags.STATION_NAME}" == '{metadata[1].lower()}'
            AND "{Tags.SERIAL_NO}" == '{metadata[3]}'
        ORDER BY "{time}" ASC;
        """
    result = client.query(query, mode="pandas")
    read_back = cast(DataFrame, result)
    print(query)
    df = read_single_campbell_logger_file(filepath)
    in_db = len(read_back)
    in_csv = len(df)
    if len(read_back) != len(df):
        raise ClickException(f"Mismatch between CSV and database. In DB: {in_db}, In CSV: {in_csv}")


@db.command(DatabaseCommands.DESCRIBE)
@station_name
@data_table
@db_options
@option("--limit", default=24, type=IntRange(min=1), help="Number of records to return")
def buoys_db_describe(name: StationName, table: TableName, limit: int, **kwargs):
    """
    Read a measurement (table) back from the
    Influx database, dropping duplicate timestamps.
    """
    time = "time"
    client = InfluxDBClient3(**kwargs)
    result = client.query(
        f"""
        SELECT * FROM (
            SELECT *, COUNT(*) OVER(PARTITION BY "{time}") as ts_count
            FROM "{table}"
            WHERE "{Tags.STATION_NAME}" == '{name.value.lower()}'
            ORDER BY "{time}" DESC
            LIMIT {limit}
        ) sub
        WHERE ts_count = 1
        """,
        mode="pandas",
    )
    read_back = cast(DataFrame, result)
    print(read_back.describe())


def delete_bucket_by_name(database: str, host: str, token: str, org: str):
    """
    Delete the InfluxDB bucket.
    """
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    find_url = f"{host}/api/v2/buckets?orgID={org}&name={database}"
    response = get(find_url, headers=headers, timeout=5)
    if response.status_code != 200:
        raise ClickException(f"Error querying bucket: {response.text}")
    result = response.json()
    if not result["buckets"]:
        raise ClickException(f"No bucket found with name: {database}")
    bucket_id = result["buckets"][0]["id"]
    if not confirm(
        f"Are you sure you want to delete the bucket '{bucket_id}'?", default=True
    ):
        raise ClickException("Bucket deletion cancelled by user.")
    delete_url = f"{host}/api/v2/buckets/{bucket_id}"
    return delete(delete_url, headers=headers, timeout=5)


@db.command(name="delete")
@db_options
def buoys_db_delete(**kwargs):
    """
    Delete the InfluxDB bucket.
    """
    response = delete_bucket_by_name(**kwargs)
    if response.status_code != 204:
        raise ClickException(f"Failed to delete bucket: {response.text}")
