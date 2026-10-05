"""
Command line interface for working with buoy database.
"""

from typing import cast
from enum import StrEnum, auto
from pandas import DataFrame
from influxdb_client_3 import InfluxDBClient3
from click import group
from lib import (
    influx_options,
    influx_host,
    influx_api_token,
)
from buoys.options import (
    StationName,
    TableName,
    VendoredNames,
    StandardNames,
    station_name,
    data_table,
    filter_buoy_flat_files,
    read_single_campbell_logger_file,
)


class DatabaseCommands(StrEnum):
    """
    Group and commands for interacting with the buoy database.
    """

    DATABASE = "db"
    DESCRIBE = auto()
    UPLOAD = auto()


@group(name=DatabaseCommands.DATABASE)
def database():
    """
    Commands that interact with the buoy database.
    """


@database.command(DatabaseCommands.DESCRIBE)
@influx_options
def buoys_db_describe(
    host: str, measurement: str, token: str
):
    """
    Read all variables in a measurement (table) back from the
    influx database.
    """
    time = "time"
    client = InfluxDBClient3(host=host, database="buoy-test", token=token)
    result = client.query(
        f"SELECT * FROM {measurement} ORDER BY {time} LIMIT 10",
        mode="pandas",
    )
    read_back = cast(DataFrame, result)
    print(read_back.head())


@database.command(name=DatabaseCommands.UPLOAD)
@station_name
@data_table
@influx_host
@influx_api_token
def buoys_db_upload(name: StationName, table: TableName, host: str, token: str):
    """
    Upload buoy data to the database.
    """
    files = list(filter_buoy_flat_files(name, table))
    client = InfluxDBClient3(host=host, database="buoy-test-3", token=token)
    columns = [VendoredNames.SEA_WATER_TEMPERATURE]
    rename = [StandardNames[key.name] for key in columns]
    for each in files:
        df = read_single_campbell_logger_file(each)
        subset = df[columns]
        subset.columns = rename
        subset.index.name = "time"
        with open(each, "r", encoding="utf-8") as fid:
            metadata = fid.readline().split(",")
        subset.insert(column="location", value=metadata[1].lower(), loc=0)
        subset.insert(column="thing", value=metadata[3], loc=1)
        subset.insert(column="firmware", value=metadata[5][5:-1], loc=2)
        client.write(
            subset,
            data_frame_measurement_name=table,
            data_frame_tag_columns=["location", "thing", "firmware"],
        )
