# pylint: disable=too-many-locals
"""
Generate a custom firmware file from a template.

Features:
- Combine column wise and row wise
- Match weather API as much as possible

"""
from pathlib import Path
from hashlib import md5
from pandas import Series, read_csv, DataFrame, concat
from datetime import datetime
from enum import Enum
import click
import re
from typing import Tuple
from lib import Source, StandardUnits, describe_data_frame, plot_tail, plot_options, boxplot

DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"

class ClickOptions(Enum):
    """
    Available commands for buoy data processing.
    """

    # file and firmware commands
    LIST = "list"
    DESCRIBE = "describe"
    TEMPLATE = "template"
    EXPORT = "export"
    # groups
    FILE = "file"
    BUOYS = "buoys"
    PLOT = "plot"
    # plotting commands
    TAIL = "tail"
    DAILY = "daily"


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


class StandardNames(Enum):
    """
    Supported data series names.
    """

    SEA_WATER_TEMPERATURE = "sea_water_temperature"
    MASS_CONCENTRATION_OF_OXYGEN_IN_SEA_WATER = (
        "mass_concentration_of_oxygen_in_sea_water"
    )
    SEA_WATER_SALINITY = "sea_water_salinity"


# pylint: disable=too-few-public-methods
class ObservedProperty:
    """
    Abstraction for a single observed property, mapping
    multiple sources into a single Schema based on CF Metadata
    standards.
    """

    name: str
    units: str
    campbell_scientific: Source

    def __init__(self, name: str, unit: str, campbell_scientific: Source):
        self.name = name
        self.unit = unit
        self.campbell_scientific = campbell_scientific


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


def source_options(function):
    """
    Choose weather station and observation series. Re-usable decorator
    for commands that need to select a station and series.
    """
    function = click.argument(
        "series", type=click.Choice(StandardNames, case_sensitive=False)
    )(function)
    function = click.argument(
        "table", type=click.Choice(TableName, case_sensitive=False)
    )(function)
    function = click.argument(
        "name", type=click.Choice(StationName, case_sensitive=False)
    )(function)
    return function


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


def read_campbell_logger_files(files: list[Path]) -> DataFrame:
    """
    Read multiple Campbell logger files and return a single DataFrame.
    """
    all_data = []
    for file in sorted(files):
        df = read_single_campbell_logger_file(file)
        # Add metadata column to be able to select overlapping data later without a join
        time_recovered = file.stem.split("_")[2]
        df["TimeRecovered"] = datetime.strptime(time_recovered, "%Y-%m-%dT%H-%M")
        all_data.append(df)
    return concat(all_data).dropna(how="all", axis=1)


def filter_buoy_flat_files(name: StationName, table: TableName):
    """
    Filter buoy flat files based on command line options.
    """
    path: Path = Path(__file__).parent.absolute() / "data"

    def filter_prefix(f: Path) -> bool:
        lower_name = f.stem.lower()
        station_match = name.value.lower() in lower_name
        table_match = table.value.lower() in lower_name
        return station_match and table_match

    return filter(filter_prefix, path.glob("*.dat"))


@file_group.command(name=ClickOptions.DESCRIBE.value)
@click.argument("name", type=click.Choice(StationName, case_sensitive=False))
@click.argument("table", type=click.Choice(TableName, case_sensitive=False))
def buoy_file_describe(name: StationName, table: TableName):
    """
    Summarize available data for a station.
    """
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(files)
    summary = df.describe().T.drop(columns=["25%", "50%", "75%", "std", "mean"])
    print("\nSamples:\n")
    print(summary)


@plot.command(name=ClickOptions.TAIL.value)
@source_options
@plot_options
def buoy_plot_tail(
    name: StationName, table: TableName, series: StandardNames, **kwargs
):
    """
    Plot the most recent data from a buoy for a single data stream.
    """
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(files)
    local: Series = df["External_Temp"].squeeze()
    local.name = "local"
    print(type(local.squeeze().index))
    plot_tail(
        local,
        None,
        name.value,
        series.value,
        prefix=f"buoys/figures/{ClickOptions.TAIL.value}",
        units=StandardUnits.TEMPERATURE.value,
        **kwargs,
    )


@plot.command(name=ClickOptions.DAILY.value)
@source_options
@plot_options
def buoy_plot_daily(name: StationName, table: TableName, series: StandardNames, **kwargs):
    """
    Plot a single `DataStream` aggregated by day.
    """
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(files)
    local = df["External_Temp"]
    mask = ~df.index.duplicated(keep=False)
    unique = local[mask].sort_index()
    unique.index.rename("time", inplace=True)
    prefix = f"buoys/figures/{ClickOptions.DAILY.value}"
    boxplot(unique, name.value, series.value, prefix, units=StandardUnits.TEMPERATURE.value, **kwargs)


@file_group.command(name=ClickOptions.EXPORT.value)
@click.argument("name", type=click.Choice(StationName, case_sensitive=False))
@click.argument("table", type=click.Choice(TableName, case_sensitive=False))
def buoy_file_export(name: StationName, table: TableName):
    """
    Export buoy data to a different format.
    """
    files = filter_buoy_flat_files(name, table)
    drop_columns = [
        "RECORD", 
        "WiperPosition",
        "Sonde_External_Voltage",
        "Sonde_Battery",
        "WiperPeakCurrent",
        "TimeRecovered",
        ("Chlorophyll", "cells/mL"),
        "BGA_PE_cellsmL",
        "Pressure_Vert_Pos",
        "Depth"
    ]
    df = read_campbell_logger_files(files).drop(columns=drop_columns)
    mask = ~df.index.duplicated(keep=False) # drop all duplicates, temporary solution
    unique = df[mask].sort_index()
    unique.index.rename("time", inplace=True)
    def format_column(col) -> str:
        # Handle columns that are not 3-tuples gracefully
        if isinstance(col, tuple) and len(col) == 3:
            name, unit, _ = col
            return f"{name} ({unit})"
        # Fallback: just return string representation
        return str(col)
    headers = list(map(format_column, unique.columns))
    print(headers)
    parts = list(filter(None, re.split(r'([A-Z][^A-Z]*)', table.value)))
    parts.insert(0, name.value)
    filename = "-".join(parts).lower() + ".csv"
    path = DATA_DIR / filename
    unique.to_csv(path, header=headers)


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
