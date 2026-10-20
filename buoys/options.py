"""
Common imports used in nested commands and the top-level group.
"""

from enum import StrEnum, auto
from warnings import simplefilter
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from click import argument, Choice, option
from pandas import read_csv, DataFrame, concat
from pandas.errors import PerformanceWarning
from lib.geo import FeatureOfInterest


DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"
EXPORT_DIR = Path(__file__).parent / "export"

class StationName(StrEnum):
    """
    Supported buoy station names.
    """

    WYNKEN = auto()
    BLYNKEN = auto()

# Canonical/reference locations for the buoy stations are kept in
# code rather than config as SensorThings Features of Interest, instead
# of Locations.
FEATURES_OF_INTEREST = {
    StationName.WYNKEN: FeatureOfInterest(
        name=StationName.WYNKEN,
        description="Planned/deployed sensor location.",
        latitude=44.0435,
        longitude=-68.8925,
    ),
    StationName.BLYNKEN: FeatureOfInterest(
        name=StationName.BLYNKEN,
        description="Planned/deployed sensor location.",
        latitude=44.318369,
        longitude=-68.926953,
    ),
}

class TableName(StrEnum):
    """
    Supported data table names.
    """

    DIAGNOSTIC = "Ai1"
    SONDE = "SondeValues"
    ANEMOMETER = "WindUltra"


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
    LATITUDE = "Latitude"
    LONGITUDE = "Longitude"
    SATELLITES_IN_VIEW = "GPSSatellitesInView"


class Source(StrEnum):
    """
    To help with determining the source format of each row in the database.
    """

    TOA5 = "TOA5"
    CSIJSON = "CSIJSON"


class Tags(StrEnum):
    """
    Metadata fields derived from first line of data file.
    """
    # Tag constants from CSI environment line
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


def parse_environment(file: Path):
    """
    Parse the environment variables for InfluxDB connection.
    """
    if not file.exists():
        raise FileNotFoundError(f"File '{file}' does not exist.")
    with open(file, "r", encoding="utf-8") as fid:
        metadata_line = fid.readline().strip()
        metadata = [item.strip('"') for item in metadata_line.split(",")]
    return metadata


def fill_metadata(df: DataFrame, file: Path) -> TableName:
    """
    Add columns to the dataframe for the metadata extracted from the
    header environment. After this step the resulting dataframe should
    be identical to what is stored in the database.
    """
    # pylint: disable=redefined-outer-name
    [
        source,  # file format, not in CSIJSON payload
        station_name,
        model,
        serial_no,
        os_version,
        prog_name,
        _,  # signature, not in CSIJSON environment payload
        table_name,
    ] = parse_environment(file)
    if source != Source.TOA5:
        raise ValueError(f"Unsupported file format '{source}'")
    if table_name not in file.stem:
        raise ValueError(f"Table '{table_name}' does not match filename '{file.name}'")
    if station_name not in file.stem:
        raise ValueError(f"Station '{station_name}' does not match filename '{file.name}'")
    df[(Tags.SOURCE, "", "")] = source
    df[(Tags.STATION_NAME, "", "")] = station_name
    df[(Tags.MODEL, "", "")] = model
    df[(Tags.SERIAL_NO, "", "")] = serial_no
    df[(Tags.OS_VERSION, "", "")] = os_version
    df[(Tags.PROG_NAME, "", "")] = prog_name
    return TableName(table_name)

def read_single_campbell_logger_file(
    file: Path
) -> DataFrame:
    """
    Read a single Campbell logger file and return a DataFrame. The time
    is assumed to be EST with Daylight Saving Time adjustments. Based 
    on when the data was recorded, the whole series is shifted and 
    update to be UTC time.
    """
    df = read_csv(file, header=[1, 2, 3], na_values=["NAN"], parse_dates=[0])
    ts_col = df.columns[0]
    df.set_index(ts_col, inplace=True)
    start: datetime = df.index.min()
    start_tz: ZoneInfo = ZoneInfo("America/New_York")
    delta: timedelta = start.tz_localize(start_tz).dst()
    df.index = (df.index - delta).tz_localize("EST").tz_convert("UTC")

    # Add metadata column to be able to select overlapping data later without a join
    try:
        time_recovered_str = file.stem.split("_")[2]
        time_recovered = datetime.strptime(time_recovered_str, "%Y-%m-%dT%H-%M")
    except (IndexError, ValueError) as exc:
        msg = f"Filename '{file.name}' does not contain a valid recovery time"
        raise ValueError(msg) from exc
    utc_recovered = (time_recovered - delta).tz_localize("EST").tz_convert("UTC")
    if utc_recovered < df.index.max():
        raise ValueError(f"Recovered time '{utc_recovered}' is before EOF in '{file.name}'")
    df["TimeRecovered"] = utc_recovered

    return df


def read_campbell_logger_files(files: list[Path]) -> DataFrame:
    """
    Read multiple Campbell logger files and return a single DataFrame.
    """
    all_data = []
    for file in sorted(files):
        df = read_single_campbell_logger_file(file)
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


def load_and_subset_multifile_table(
    name: StationName,
    table: TableName,
    start: Optional[datetime],
    end: Optional[datetime],
    omit: Optional[list[str|tuple[str, str]]] = None,
) -> tuple[DataFrame, list]:
    """
    Load and subset a multi-file table for a given station and table name, returning
    a DataFrame with data between the specified start and end dates.
    """
    simplefilter(action="ignore", category=PerformanceWarning)
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(list(files))
    if omit is not None:
        df = df.drop(columns=omit, errors="ignore")
    _end = end if end is not None else datetime.now()
    mask = (df.index <= _end)
    if start is not None:
        mask &= (df.index > start)
    df = df[mask].sort_values("TimeRecovered").drop(columns=["TimeRecovered"], errors="ignore")
    duplicates = df.index.duplicated(keep="first")
    dropped = df[duplicates].index.to_list()
    df = df[~duplicates].sort_index(kind="stable")
    resampled = df.asfreq("h")  # Resample and fill gaps with NaN to force gaps when plotting
    return resampled, dropped
