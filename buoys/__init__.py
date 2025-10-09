# pylint: disable=too-many-locals
"""
Generate a custom firmware file from a template.

Features:
- Combine column wise and row wise
- Match weather API as much as possible

"""
from pathlib import Path
from hashlib import md5
from pandas import read_csv, DataFrame, concat
from datetime import datetime
from enum import Enum
import click
from lib import Source, StandardUnits


class ClickOptions(Enum):
    """
    Available commands for buoy data processing.
    """

    LIST = "list"
    DESCRIBE = "describe"
    TEMPLATE = "template"
    FILE = "file"
    BUOYS = "buoys"
    PLOT = "plot"


class StationName(Enum):
    """
    Supported buoy station names.
    """

    WYNKEN = "wynken"
    BLYNKEN = "blynken"

class TableName(Enum):
    """
    Supported data table names.
    """

    DIAGNOSTIC = "Ai1"
    SONDE = "SondeValues"

class SeriesNames(Enum):
    """
    Supported data series names.
    """
    TEMPERATURE = "External_Temp"

@click.group(name=ClickOptions.BUOYS.value)
def buoys():
    """
    Command line interface for working with buoy data and firmware.
    """


@click.group(name=ClickOptions.PLOT.value)
def plot():
    """
    Commands that generate plots using buoy data.
    """


@click.group(name=ClickOptions.FILE.value)
def file_group():
    """
    Commands that interact with the weather file system.
    """


# Subcommands assignment
buoys.add_command(plot)
buoys.add_command(file_group)


@file_group.command(name=ClickOptions.LIST.value)
def list_buoys():
    """
    List available stations from static data.
    """
    path = Path(__file__).parent.absolute()
    firmware_path = f"{path}/data"
    files = sorted(Path(firmware_path).glob("*.dat"))
    seen = set()
    for f in files:
        station = f.stem.split("_")[0]
        if station not in seen:
            print(station)
            seen.add(station)

def read_single_campbell_logger_file(file: Path) -> DataFrame:
    """
    Read a single Campbell logger file and return a DataFrame.
    """
    df = read_csv(file, header=[1, 2, 3], na_values=["NAN"], parse_dates=[0])
    ts_col = df.columns[0]
    return df.set_index(ts_col)

def read_and_concatenate

@file_group.command(name=ClickOptions.DESCRIBE.value)
@click.argument("name", type=click.Choice(StationName, case_sensitive=False))
@click.argument("table", type=click.Choice(TableName, case_sensitive=False))
def buoys_describe_series(name: StationName, table: TableName):
    """
    Summarize available data for a station.
    """
    path: Path = Path(__file__).parent.absolute() / "data"

    def filter_prefix(f: Path) -> bool:
        lower_name = f.stem.lower()
        station_match = name.value.lower() in lower_name
        table_match = table.value.lower() in lower_name
        return station_match and table_match

    files = filter(filter_prefix, path.glob("*.dat"))
    all_data = []
    for file in sorted(files):
        df = read_single_campbell_logger_file(file)
        # Add metadata column to be able to select overlapping data later without a join
        time_recovered = file.stem.split("_")[2]
        df["TimeRecovered"] = datetime.strptime(time_recovered, "%Y-%m-%dT%H-%M")
        all_data.append(df)
    _df = concat(all_data).dropna(how="all", axis=1)
    print(_df.info())
    print(_df.index.duplicated().sum(), "duplicate rows")


@buoys.command(name=ClickOptions.TEMPLATE.value)
@click.option("--name", required=True, help="Station name")
@click.option("--address", required=True, help="Pakbus address")
@click.option("--client", required=True, help="Client ID")
@click.option("--file", default="buoy.dld", help="Template file")
def template(name: str, address: str, client: str, file: str):
    """
    Fill in firmware template with options passed on
    the command line.
    """
    path = Path(__file__).parent.absolute()
    template_path = f"{path}/templates/{file}"
    with open(template_path, "r", encoding="utf-8") as fid:
        filedata = fid.read()

    for var, value in {
        "STATION_NAME": name,
        "PAKBUS_ADDRESS": address,
        "CLIENT_ID": client,
    }.items():
        slug = "$" + var
        filedata = filedata.replace(slug, value)

    encoded_data = filedata.encode("utf-8")
    hasher = md5()
    hasher.update(encoded_data)
    checksum = hasher.hexdigest()
    prefix = name.lower()
    firmware = f"{path}/firmware/{prefix}.{checksum}.dld"
    Path(firmware).parent.mkdir(parents=True, exist_ok=True)
    with open(firmware, "w", encoding="utf-8") as fid:
        fid.write(filedata)
