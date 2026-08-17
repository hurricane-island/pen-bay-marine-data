"""
Command line interface for working with buoy database.
"""

from pathlib import Path
from enum import Enum
from pandas import DataFrame
from influxdb_client_3 import InfluxDBClient3
from click import group
from lib import (
    influx_options,
    influx_host,
    influx_api_token,
)
from buoys import (
    buoys,
    station_name,
    data_table,
    filter_buoy_flat_files,
    read_single_campbell_logger_file,
    StationName,
    TableName,
    VendoredNames,
    StandardNames,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class DatabaseCommands(Enum):
    DATABASE = "db"
    UPLOAD = "upload"
    DESCRIBE = "describe"


@group(name=DatabaseCommands.DATABASE.value)
def database():
    """
    Commands that interact with the buoy database.
    """


buoys.add_command(database)


@database.command(name="upload")
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
    # columns = [VendoredNames.SEA_WATER_TEMPERATURE, VendoredNames.SEA_WATER_SALINITY]
    columns = [VendoredNames.SEA_WATER_TEMPERATURE]
    rename = [StandardNames[key.name].value for key in columns]
    for each in files:
        df = read_single_campbell_logger_file(each)
        subset = df[[key.value for key in columns]]
        subset.columns = rename
        subset.index.name = "time"
        with open(each, "r", encoding="utf-8") as fid:
            metadata = fid.readline().split(",")
        subset.insert(column="location", value=metadata[1].lower(), loc=0)
        subset.insert(column="thing", value=metadata[3], loc=1)
        subset.insert(column="firmware", value=metadata[5][5:-1], loc=2)
        client.write(
            subset,
            data_frame_measurement_name=table.value,
            data_frame_tag_columns=["location", "thing", "firmware"],
        )


@database.command(DatabaseCommands.DESCRIBE.value)
@station_name
@data_table
@influx_options
def buoys_db_describe(
    name: StationName, table: TableName, host: str, measurement: str, token: str
):
    time = "time"
    client = InfluxDBClient3(host=host, database="buoy-test", token=token)
    read_back: DataFrame = client.query(
        f"SELECT * FROM {measurement} ORDER BY {time} LIMIT 10",
        mode="pandas",
    )
    print(read_back.head())
