# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
"""
Weather Station Tools CLI:

This module provides a command-line interface for using weather station data, including:

- `export`:Concatenate CSV files from a single station
- `describe`: Show summary statistics for a station
- `db`: Get information about the Influx database
- TBD: Backfill Influx database from CSV files
- Convert CSV names to WeeWx/InfluxDB names

Limitations:

- Cannot delete or drop measurements from Cloud Serverless (immutable Parquet)

Questions:

- What happens when a partial merge is attempted?
- What happens when two identical timestamps exist in a measurement?

"""

from pathlib import Path
from enum import Enum
import click
from pandas import read_csv, to_datetime, DataFrame, Series, concat
from influxdb_client_3 import InfluxDBClient3
from lib import (
    plot_options,
    influx_options,
    boxplot,
    plot_tail,
    fahrenheit_to_kelvin,
    cardinal_direction_to_degrees,
    describe_data_frame,
    StandardUnits
)


DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"
TIME = "time"
KNOTS_TO_SPEED = 0.514444
INCHES_OF_MERCURY_TO_PRESSURE = 3386.389
MILES_PER_HOUR_TO_SPEED = 0.44704
PERCENT_TO_FRACTION = 0.01
INCHES_TO_MILLIMETERS = 25.4
INCHES_PER_HOUR_TO_KILOGRAMS_PER_SQUARE_METER_PER_SECOND = INCHES_TO_MILLIMETERS / 3600


class ClickCommands(Enum):
    """
    Valid click command names. Does not factor in
    Click groups. Used to ensure consistent command
    and label usage across CLI.
    """

    # plotting commands
    TAIL = "tail"
    DAILY = "daily"
    # db and file commands...
    DESCRIBE = "describe"
    BACKFILL = "backfill"
    EXPORT = "export"


# pylint: disable=too-few-public-methods
class Source:
    """
    Abstraction for converting from a data source
    to standard format.
    """

    name: str
    transform: callable

    def __init__(self, name: str, transform: callable):
        self.name = name
        self.transform = transform


# pylint: disable=too-few-public-methods
class ObservedProperty:
    """
    Abstraction for a single observed property, mapping
    multiple sources into a single Schema based on CF Metadata
    standards.
    """

    name: str
    units: str
    weewx: Source
    weather_link: Source

    def __init__(self, name: str, unit: str, weewx: Source, weather_link: Source):
        self.name = name
        self.unit = unit
        self.weewx = weewx
        self.weather_link = weather_link


class StandardNames(Enum):
    """
    CF Metadata Standard Names. These are all of the Davis Vantage Pro2
    observed properties that have Climate and Forecast (CF) metadata standard
    names. Not all of these are available on all platforms, but it is
    a starting point from what we currently have in the field.
    """

    AIR_TEMPERATURE = "air_temperature"
    RELATIVE_HUMIDITY = "relative_humidity"
    WIND_SPEED = "wind_speed"
    WIND_FROM_DIRECTION = "wind_from_direction"
    AIR_PRESSURE = "air_pressure"
    WIND_SPEED_OF_GUST = "wind_speed_of_gust"
    WIND_GUST_FROM_DIRECTION = "wind_gust_from_direction"
    WIND_CHILL_OF_AIR_TEMPERATURE = "wind_chill_of_air_temperature"
    SOLAR_IRRADIANCE = "solar_irradiance"
    ULTRAVIOLET_INDEX = "ultraviolet_index"
    RAINFALL_AMOUNT = "rainfall_amount"
    RAINFALL_RATE = "rainfall_rate"
    HEAT_INDEX_OF_AIR_TEMPERATURE = "heat_index_of_air_temperature"
    DEW_POINT_TEMPERATURE = "dew_point_temperature"
    WATER_EVAPOTRANSPIRATION_FLUX = "water_evapotranspiration_flux"


# Standard units for display, not used in determining value conversions
CF_STANDARDS = {
    StandardNames.AIR_TEMPERATURE: ObservedProperty(
        name=StandardNames.AIR_TEMPERATURE.value,
        unit=StandardUnits.TEMPERATURE.value,
        weather_link=Source(name="Temp Out", transform=fahrenheit_to_kelvin),
        weewx=Source(name="outTemp", transform=fahrenheit_to_kelvin),
    ),
    StandardNames.RELATIVE_HUMIDITY: ObservedProperty(
        name=StandardNames.RELATIVE_HUMIDITY.value,
        unit=None,
        weather_link=Source(
            name="Out Hum", transform=lambda x: x * PERCENT_TO_FRACTION
        ),
        weewx=Source(name="outHumidity", transform=lambda x: x * PERCENT_TO_FRACTION),
    ),
    StandardNames.WIND_SPEED: ObservedProperty(
        name=StandardNames.WIND_SPEED.value,
        unit=StandardUnits.SPEED.value,
        weather_link=Source(
            name="Wind Speed",
            transform=lambda x: x * MILES_PER_HOUR_TO_SPEED,
        ),
        weewx=Source(name="windSpeed", transform=lambda x: x * KNOTS_TO_SPEED),
    ),
    StandardNames.WIND_FROM_DIRECTION: ObservedProperty(
        name=StandardNames.WIND_FROM_DIRECTION.value,
        unit=StandardUnits.DIRECTION.value,
        weather_link=Source(name="Wind Dir", transform=lambda x: x),
        weewx=Source(name="windDir", transform=cardinal_direction_to_degrees),
    ),
    StandardNames.AIR_PRESSURE: ObservedProperty(
        name=StandardNames.AIR_PRESSURE.value,
        unit=StandardUnits.PRESSURE.value,
        weather_link=Source(
            name="Bar", transform=lambda x: x * INCHES_OF_MERCURY_TO_PRESSURE
        ),
        weewx=Source(
            name="barometer", transform=lambda x: x * INCHES_OF_MERCURY_TO_PRESSURE
        ),
    ),
    StandardNames.WIND_SPEED_OF_GUST: ObservedProperty(
        name=StandardNames.WIND_SPEED_OF_GUST.value,
        unit=StandardUnits.SPEED.value,
        weather_link=Source(
            name="Hi Speed", transform=lambda x: x * MILES_PER_HOUR_TO_SPEED
        ),
        weewx=Source(name="windGust", transform=lambda x: x * KNOTS_TO_SPEED),
    ),
    StandardNames.WIND_GUST_FROM_DIRECTION: ObservedProperty(
        name=StandardNames.WIND_GUST_FROM_DIRECTION.value,
        unit=StandardUnits.DIRECTION.value,
        weather_link=Source(name="Hi Dir", transform=lambda x: x),
        weewx=Source(name="windGustDir", transform=cardinal_direction_to_degrees),
    ),
    StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE: ObservedProperty(
        name=StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value,
        unit=StandardUnits.TEMPERATURE.value,
        weather_link=Source(name="Wind Chill", transform=fahrenheit_to_kelvin),
        weewx=Source(name="windchill", transform=fahrenheit_to_kelvin),
    ),
    StandardNames.SOLAR_IRRADIANCE: ObservedProperty(
        name=StandardNames.SOLAR_IRRADIANCE.value,
        unit=StandardUnits.ENERGY.value,
        weather_link=Source(name="Solar Rad.", transform=lambda x: x),
        weewx=Source(name="radiation", transform=lambda x: x),
    ),
    StandardNames.ULTRAVIOLET_INDEX: ObservedProperty(
        name=StandardNames.ULTRAVIOLET_INDEX.value,
        unit=None,
        weather_link=Source(name="UV Index", transform=lambda x: x),
        weewx=Source(name="UV", transform=lambda x: x),
    ),
    StandardNames.RAINFALL_AMOUNT: ObservedProperty(
        name=StandardNames.RAINFALL_AMOUNT.value,
        unit=StandardUnits.AMOUNT.value,
        weather_link=Source(name="Rain", transform=lambda x: x * INCHES_TO_MILLIMETERS),
        weewx=Source(name="rain", transform=lambda x: x * INCHES_TO_MILLIMETERS),
    ),
    StandardNames.RAINFALL_RATE: ObservedProperty(
        name=StandardNames.RAINFALL_RATE.value,
        unit=StandardUnits.FLUX.value,
        weather_link=Source(
            name="Rain Rate",
            transform=lambda x: x
            * INCHES_PER_HOUR_TO_KILOGRAMS_PER_SQUARE_METER_PER_SECOND,
        ),
        weewx=Source(
            name="rainRate",
            transform=lambda x: x
            * INCHES_PER_HOUR_TO_KILOGRAMS_PER_SQUARE_METER_PER_SECOND,
        ),
    ),
    StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE: ObservedProperty(
        name=StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value,
        unit=StandardUnits.TEMPERATURE.value,
        weather_link=Source(name="Heat Index", transform=fahrenheit_to_kelvin),
        weewx=Source(name="heatindex", transform=fahrenheit_to_kelvin),
    ),
    StandardNames.DEW_POINT_TEMPERATURE: ObservedProperty(
        name=StandardNames.DEW_POINT_TEMPERATURE.value,
        unit=StandardUnits.TEMPERATURE.value,
        weather_link=Source(name="Dew Pt.", transform=fahrenheit_to_kelvin),
        weewx=Source(name="dewpoint", transform=fahrenheit_to_kelvin),
    ),
    StandardNames.WATER_EVAPOTRANSPIRATION_FLUX: ObservedProperty(
        name=StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value,
        unit=StandardUnits.FLUX.value,
        weewx=Source(
            name="ET",
            transform=lambda x: x
            * INCHES_PER_HOUR_TO_KILOGRAMS_PER_SQUARE_METER_PER_SECOND,
        ),
        weather_link=Source(
            name="ET",
            transform=lambda x: x
            * INCHES_PER_HOUR_TO_KILOGRAMS_PER_SQUARE_METER_PER_SECOND,
        ),
    ),
}


class StationName(Enum):
    """
    Valid station names. For now just includes weather
    stations, but these could be used to refer to all
    sensing platforms and systems at a single location.
    """

    APPRENTICESHOP = "apprenticeshop"
    DEV = "dev"


@click.group(name="weather")
def weather():
    """
    Weather station commands.
    """


@click.group(name="plot")
def plot():
    """
    Commands that generate plots using weather data.
    """


@click.group(name="db")
def database():
    """
    Commands that interact with the weather database.
    """


@click.group(name="file")
def file():
    """
    Commands that interact with the weather file system.
    """


# Subcommands assignment
weather.add_command(plot)
weather.add_command(database)
weather.add_command(file)


def source_options(function):
    """
    Choose weather station and observation series.
    """
    function = click.argument(
        "series", type=click.Choice(StandardNames, case_sensitive=False)
    )(function)
    function = click.argument(
        "station", type=click.Choice(StationName, case_sensitive=False)
    )(function)
    return function


# pylint: disable=too-few-public-methods
class WeatherLinkArchive:
    """
    A WeatherLink archive exported file
    """

    # pylint: disable=too-many-arguments, too-many-locals, too-many-positional-arguments
    def __init__(
        self,
        # Source name
        name: str,
        # Number of rows that contain column info to concatenate
        skiprows: int = 2,
        # Delimiter used in the sourcefile
        delimiter: str = "\t",
        # Interpret as NaN
        na_value: str = "---",
        # Name of date column
        date: str = "Date",
        # Name of time column
        time: str = "Time",
    ):
        """
        Read and normalize weather station data. This handles
        parsing a Davis WeatherLink export. This format contains
        two lines of headers, is tab-delimited, and has separate
        columns for data and time that need to be combined.

        Normalize headers from a multiple header line file. Rename them if they
        have a known mapping, but otherwise leave them as is.
        """
        self.name = name
        filename = DATA_DIR / f"{name}.txt"
        rows: list[list[str]] = []
        with open(filename, "r", encoding="utf-8") as fid:
            for _ in range(skiprows):
                rows.append(fid.readline().split(delimiter))
        names = []
        lookup = {}
        transforms = {}
        for key, value in CF_STANDARDS.items():
            lookup[value.weather_link.name] = key.value
            transforms[key.value] = value.weather_link.transform

        for items in zip(*rows):
            header = ""
            for each in items:
                header += str(each).strip() + " "
            header = header.strip()
            names.append(lookup.get(header, header))
        df = read_csv(
            filename,
            delimiter=delimiter,
            skiprows=skiprows,
            names=names,
            na_values=[na_value],
        )
        # create a string that can be parsed as a datetime by pandas
        time_string = df[date] + " " + df[time].str.upper() + "M"
        series = Series(time_string, name=TIME)
        timestamps = to_datetime(series, format="%m/%d/%y %I:%M %p")
        df.set_index(timestamps, inplace=True)
        df.drop(columns=[date, time], inplace=True)
        self.df = df.transform(transforms)


class WeeWxInfluxArchive:
    """
    WeeWx archive data from InfluxDB.
    """

    # pylint: disable=redefined-outer-name
    def __init__(
        self,
        measurement: str,
        token: str,
        host: str,
        time: str = TIME,
        database: str = "weather",
    ):
        """
        Get data from InfluxDB and format as a DataFrame.
        """
        client = InfluxDBClient3(host=host, database=database, token=token)
        df: DataFrame = client.query(
            f"SELECT * FROM {measurement} WHERE binding IN ('archive') ORDER BY {time}",
            mode="pandas",
        )
        # Invert the dictionary, keeping the second value as key
        columns = {}
        transforms = {}
        for key, value in CF_STANDARDS.items():
            columns[value.weewx.name] = key.value
            transforms[key.value] = value.weewx.transform
        df.rename(columns=columns, inplace=True)
        df.set_index(time, inplace=True)
        self.df = df.transform(transforms)


@weather.command(name=ClickCommands.DESCRIBE.value)
@source_options
@influx_options
def weather_describe_series(
    station: StandardNames,
    series: StandardNames,
    host: str,
    measurement: str,
    token: str,
):
    """
    Compare local and database data before merging or backfilling.
    """
    db = WeeWxInfluxArchive(measurement, token, host).df[series.value]
    local = WeatherLinkArchive(station.value).df[series.value]
    db.name = "influx"
    local.name = "local"
    df = concat([db, local], axis=1)
    print(df.describe())


@plot.command(name=ClickCommands.TAIL.value)
@source_options
@influx_options
@plot_options
@click.option(
    "--days",
    default=60,
    help="The time range to include in the plot (e.g., 7, 14).",
)
@click.option(
    "--resample",
    default="1h",
    help="How to resample the data (e.g., 1d, 1h).",
)
def weather_plot_tail(
    station: StationName,
    series: StandardNames,
    host: str,
    measurement: str,
    token: str,
    **kwargs,
):
    """
    Plot a comparison of local and InfluxDB data for a specific series.

    Keyword arguments are passed through to the rendering function
    """
    remote = WeeWxInfluxArchive(measurement, token, host).df[series.value]
    local = WeatherLinkArchive(station.value).df[series.value]
    prefix = f"{FIGURES_DIR}/{ClickCommands.TAIL.value}"
    unit = CF_STANDARDS.get(series).unit
    plot_tail(local, remote, station.value, series.value, prefix, units=unit, **kwargs)


@plot.command(name=ClickCommands.DAILY.value)
@source_options
@influx_options
@plot_options
# pylint: disable=too-many-locals,redefined-builtin
def weather_plot_daily(
    station: StationName,
    series: Enum,
    host: str,
    measurement: str,
    token: str,
    **kwargs,
):
    """
    Display a single `DataStream` aggregated by day.
    """
    remote = WeeWxInfluxArchive(measurement, token, host).df[series.value]
    local = WeatherLinkArchive(station.value).df[series.value]
    df = concat([local, remote], axis=0)
    mask = ~df.index.duplicated(keep="first")
    unique = df[mask].sort_index()
    units = CF_STANDARDS.get(series).unit
    prefix = f"{FIGURES_DIR}/{ClickCommands.DAILY.value}"
    boxplot(unique, station.value, series.value, prefix, units, **kwargs)


@file.command(name=ClickCommands.DESCRIBE.value)
@click.argument("station", type=click.Choice(StationName, case_sensitive=False))
def weather_file_describe(station: StationName):
    """
    Parse and normalize weather station data for display
    """
    df = WeatherLinkArchive(station.value).df
    describe_data_frame(df, f"{Path(__file__).parent}/qartod.yaml")


@file.command(name=ClickCommands.EXPORT.value)
@click.argument("station", type=click.Choice(StationName, case_sensitive=False))
def weather_file_export(station: StationName):
    """
    Export normalized weather station data to CSV.
    """
    df = WeatherLinkArchive(station.value).df
    filename = DATA_DIR / f"{station.value}.csv"
    df.to_csv(filename)


@database.command(name=ClickCommands.DESCRIBE.value)
@influx_options
def weather_db_describe(host: str, measurement: str, token: str):
    """
    Show information about the data already stored in Influx database.
    """
    df = WeeWxInfluxArchive(measurement, token, host).df
    describe_data_frame(df, f"{Path(__file__).parent}/qartod.yaml")


@database.command(name=ClickCommands.BACKFILL.value)
@click.argument("station", type=click.Choice(StationName, case_sensitive=False))
@influx_options
def weather_db_backfill(station: StationName, host: str, measurement: str, token: str):
    """
    Backfill missing data from local to database.
    """
    local = WeatherLinkArchive(station.value).df
    remote = WeeWxInfluxArchive(measurement, token, host).df
    selected = [each.value for each in StandardNames]
    filtered = local[selected]
    remote_filtered = remote[selected]
    filtered["station"] = station.value
    filtered["device"] = "davis-vantage"
    filtered["source"] = "weather-link"

    remote_filtered["station"] = station.value
    remote_filtered["device"] = "davis-vantage"
    remote_filtered["source"] = "weewx"

    df = concat([filtered, remote_filtered]).drop_duplicates(
        keep="first", ignore_index=False
    )

    with InfluxDBClient3(host=host, database="neracoos", token=token) as client:
        client.write(
            df,
            data_frame_measurement_name="weather",
            data_frame_tag_columns=["station", "device", "source"],
        )
