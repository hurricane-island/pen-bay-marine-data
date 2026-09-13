"""
Common imports used in nested commands and the top-level group.
"""

from enum import StrEnum, auto
from pathlib import Path
from datetime import datetime
from click import argument, Choice, option
from pandas import read_csv, DataFrame, concat


DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"
EXPORT_DIR = Path(__file__).parent / "export"
CABLE_DIR = Path(__file__).parent / "cable"


class StationName(StrEnum):
    """
    Supported buoy station names.
    """

    WYNKEN = auto()
    BLYNKEN = auto()


class TableName(StrEnum):
    """
    Supported data table names.
    """

    DIAGNOSTIC = "Ai1"
    SONDE = "SondeValues"


class VendoredNames(StrEnum):
    """
    Names that are used in the raw data but don't conform to CF Metadata standards.
    These are mapped to `StandardNames` for use in the CLI and plotting functions.
    """

    SEA_WATER_TEMPERATURE = "External_Temp"
    SEA_WATER_SALINITY = "Salinity"
    SEA_WATER_CHLOROPHYLL_RFU = "Chlorophyll_RFU"
    SEA_WATER_PHYCOERYTHRIN_RFU = "BGA_PE_RFU"
    BAROMETRIC_PRESSURE = "Pressure_mH2O"
    BATTERY_VOLTAGE = "BatteryVoltage"
    WATER_PRESSURE = "Pressure_abs"
    DISSOLVED_OXYGEN = "ODO"
    DISSOLVED_OXYGEN_SATURATION = "ODO_Sat"


class StandardNames(StrEnum):
    """
    Supported data series names.
    """

    SEA_WATER_TEMPERATURE = "sea_water_temperature"
    MASS_CONCENTRATION_OF_OXYGEN_IN_SEA_WATER = (
        "mass_concentration_of_oxygen_in_sea_water"
    )
    SEA_WATER_SALINITY = "sea_water_salinity"
    SEA_WATER_CHLOROPHYLL_RFU = "sea_water_chlorophyll_rfu"
    SEA_WATER_PHYCOERYTHRIN_RFU = "sea_water_phycoerythrin_rfu"
    BAROMETRIC_PRESSURE = "barometric_pressure"
    BATTERY_VOLTAGE = "battery_voltage"
    WATER_PRESSURE = "sea_water_pressure"
    DISSOLVED_OXYGEN = "dissolved_oxygen"
    DISSOLVED_OXYGEN_SATURATION = "dissolved_oxygen_saturation"


station_name = argument(
    "name", type=Choice(StationName, case_sensitive=False)
)
data_table = argument("table", type=Choice(TableName, case_sensitive=False))


def source_options(function):
    """
    Choose weather station and observation series. Re-usable decorator
    for commands that need to select a station and series.
    """
    function = argument(
        "series", type=Choice(StandardNames, case_sensitive=False)
    )(function)
    function = data_table(function)
    function = station_name(function)
    return function

def figure_size(default_size: tuple[float, float]):
    """
    Decorator to add a --figsize option to a Click command.
    """

    def decorator(cmd):
        return option(
            "--figsize",
            nargs=2,
            default=default_size,
            help="Size of the output figure in inches (width, height).",
        )(cmd)

    return decorator


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

    def filter_prefix(f: Path) -> bool:
        lower_name = f.stem.lower()
        station_match = name.lower() in lower_name
        table_match = table.lower() in lower_name
        return station_match and table_match

    return filter(filter_prefix, DATA_DIR.glob("*.dat"))
