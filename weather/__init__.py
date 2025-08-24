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

from os import getenv
from datetime import datetime
from pathlib import Path
from enum import Enum
import click
from pandas import read_csv, to_datetime, DataFrame, Series, concat, Grouper
from influxdb_client_3 import InfluxDBClient3
from matplotlib import pyplot as plt, dates as mdates
from matplotlib.axes import Axes
from balena import Balena


DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"
TIME = "time"
KNOTS_TO_METERS_PER_SECOND = 0.514444
INCHES_OF_MERCURY_TO_PASCAL = 3386.389
MILES_PER_HOUR_TO_METERS_PER_SECOND = 0.44704


class StandardNames(Enum):
    """
    CF Metadata Standard Names
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


CF_STANDARD_NAME_TO_UNITS = {
    StandardNames.AIR_TEMPERATURE.value: "deg K",
    StandardNames.RELATIVE_HUMIDITY.value: None,
    StandardNames.WIND_SPEED.value: "m / s",
    StandardNames.WIND_FROM_DIRECTION.value: "degrees",
    StandardNames.AIR_PRESSURE.value: "Pa",
    StandardNames.WIND_SPEED_OF_GUST.value: "m / s",
    StandardNames.WIND_GUST_FROM_DIRECTION.value: "degrees",
    StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value: "deg K",
    StandardNames.SOLAR_IRRADIANCE.value: "W / m^2",
    StandardNames.ULTRAVIOLET_INDEX.value: None,
    StandardNames.RAINFALL_AMOUNT.value: "kg / m^2",
    StandardNames.RAINFALL_RATE.value: "kg / m^2 / s",
    StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value: "deg K",
    StandardNames.DEW_POINT_TEMPERATURE.value: "deg K",
    StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value: "kg / m^2 / s",
}

# Weather Link to WeeWx mapping, the keys
# are reordered into logical groupings
# and are not in column-order
CF_STANDARD_NAME_TO_DAVIS_WEEWX = {
    StandardNames.AIR_TEMPERATURE.value: ["Temp Out", "outTemp"],  # float64, F -> K
    StandardNames.RELATIVE_HUMIDITY.value: ["Out Hum", "outHumidity"],  # float64, %
    StandardNames.WIND_SPEED.value: [
        "Wind Speed",
        "windSpeed",
    ],  # UNIT MISMATCH, knots -> miles per hour -> m/s
    StandardNames.WIND_FROM_DIRECTION.value: [
        "Wind Dir",
        "windDir",
    ],  # DATA TYPE MISMATCH & SOME DATA MISSING FROM DB, cardinal -> degrees
    StandardNames.AIR_PRESSURE.value: ["Bar", "barometer"],  # float64, Hg -> Pa
    StandardNames.WIND_SPEED_OF_GUST.value: [
        "Hi Speed",
        "windGust",
    ],  # UNIT MISMATCH, knots -> miles per hour -> m/s
    StandardNames.WIND_GUST_FROM_DIRECTION.value: [
        "Hi Dir",
        "windGustDir",
    ],  # DATA TYPE AND OFFSET(?) MISMATCH
    StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value: [
        "Wind Chill",
        "windchill",
    ],  # float64
    StandardNames.SOLAR_IRRADIANCE.value: ["Solar Rad.", "radiation"],  # float64
    StandardNames.ULTRAVIOLET_INDEX.value: ["UV Index", "UV"],  # float64
    StandardNames.RAINFALL_AMOUNT.value: ["Rain", "rain"],  # float64
    StandardNames.RAINFALL_RATE.value: ["Rain Rate", "rainRate"],  # float64
    StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value: [
        "Heat Index",
        "heatindex",
    ],  # float64
    StandardNames.DEW_POINT_TEMPERATURE.value: ["Dew Pt.", "dewpoint"],  # float64
    StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value: ["ET", "ET"],  # float64
}


class ClickCommands(Enum):
    """
    Valid click command names
    """

    EXPORT = "export"
    COMPARE = "compare"
    TAIL = "tail"
    DAILY = "daily"
    DESCRIBE = "describe"
    INFLUX = "influx"
    STATS = "stats"
    BACKFILL = "backfill"
    DEPLOY = "deploy"
    QUALITY = "quality"


class ImageFormat(Enum):
    """
    Valid image file formats for writing figures
    """

    PNG = "png"


class StationName(Enum):
    """Valid weather station names"""

    APPRENTICESHOP = "apprenticeshop"
    DEV = "dev"


@click.group()
def weather():
    """
    Weather station commands.
    """


@click.group()
def plot():
    """
    Commands that generate plots using weather data.
    """


# Subcommands assignment
weather.add_command(plot)


def source_options(function):
    """
    Attach common options to source commands:
    - host
    - token
    - measurement
    - station
    - series
    """
    function = click.option(
        "--token",
        envvar="INFLUX_API_TOKEN",
        help="The InfluxDB API token.",
    )(function)
    function = click.option(
        "--measurement",
        default="observations",
        help="The InfluxDB measurement (table) name.",
    )(function)
    function = click.option(
        "--host",
        envvar="INFLUX_SERVER_URL",
        help="The InfluxDB server URL.",
    )(function)
    function = click.argument(
        "series", type=click.Choice(StandardNames, case_sensitive=False)
    )(function)
    function = click.argument(
        "station", type=click.Choice(StationName, case_sensitive=False)
    )(function)
    return function


def plot_options(function):
    """
    Attach common options to plotting commands.
    """
    function = click.option(
        "--format",
        type=click.Choice(ImageFormat, case_sensitive=False),
        default=ImageFormat.PNG,
        help="The output format.",
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
        with open(filename, "r", encoding="utf-8") as file:
            for _ in range(skiprows):
                rows.append(file.readline().split(delimiter))
        names = []
        lookup = {
            value[0]: key for key, value in CF_STANDARD_NAME_TO_DAVIS_WEEWX.items()
        }
        for items in zip(*rows):
            header = ""
            for each in items:
                header += str(each).strip() + " "
            header = header.strip()
            if header in lookup:
                header = lookup[header]
            names.append(header)
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
        df = df.drop(columns=[date, time])
        self.df = df
        self.unit_correction()

    def __repr__(self):
        return f"Archive(name={self.name})"

    def unit_correction(self):
        """
        Exported speed is in knots, but standard is m / s.
        Exported direction is cardinal, but standard is in degrees.
        """
        self.df[StandardNames.WIND_SPEED.value] = (
            self.df[StandardNames.WIND_SPEED.value] * KNOTS_TO_METERS_PER_SECOND
        )
        self.df[StandardNames.WIND_SPEED_OF_GUST.value] = (
            self.df[StandardNames.WIND_SPEED_OF_GUST.value] * KNOTS_TO_METERS_PER_SECOND
        )
        wind = {
            "N": 0,
            "NNE": 22.5,
            "NE": 45,
            "ENE": 67.5,
            "E": 90,
            "ESE": 112.5,
            "SE": 135,
            "SSE": 157.5,
            "S": 180,
            "SSW": 202.5,
            "SW": 225,
            "WSW": 247.5,
            "W": 270,
            "WNW": 292.5,
            "NW": 315,
            "NNW": 337.5,
        }
        self.df[StandardNames.WIND_FROM_DIRECTION.value] = self.df[
            StandardNames.WIND_FROM_DIRECTION.value
        ].map(wind)
        self.df[StandardNames.WIND_GUST_FROM_DIRECTION.value] = self.df[
            StandardNames.WIND_GUST_FROM_DIRECTION.value
        ].map(wind)
        self.df[StandardNames.AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.AIR_TEMPERATURE.value] + 459.67) * 5 / 9
        )
        self.df[StandardNames.DEW_POINT_TEMPERATURE.value] = (
            (self.df[StandardNames.DEW_POINT_TEMPERATURE.value] + 459.67) * 5 / 9
        )
        self.df[StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value] + 459.67)
            * 5
            / 9
        )
        self.df[StandardNames.AIR_PRESSURE.value] = (
            self.df[StandardNames.AIR_PRESSURE.value] * INCHES_OF_MERCURY_TO_PASCAL
        )
        self.df[StandardNames.RELATIVE_HUMIDITY.value] = (
            self.df[StandardNames.RELATIVE_HUMIDITY.value] * 0.01
        )
        # density and length units cancel out
        self.df[StandardNames.RAINFALL_AMOUNT.value] = (
            self.df[StandardNames.RAINFALL_AMOUNT.value] * 25.4
        )
        self.df[StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value] = (
            self.df[StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value] * 25.4 / 3600
        )
        self.df[StandardNames.RAINFALL_RATE.value] = (
            self.df[StandardNames.RAINFALL_RATE.value] * 25.4 / 3600
        )
        self.df[StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value] + 459.67)
            * 5
            / 9
        )
        # none for irradiance, UV


class WeeWxInfluxArchive:
    """
    WeeWx archive data from InfluxDB.
    """

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
        self.df: DataFrame = client.query(
            f"SELECT * FROM {measurement} WHERE binding IN ('archive') ORDER BY {time}",
            mode="pandas",
        )
        columns = {
            value[1]: key for key, value in CF_STANDARD_NAME_TO_DAVIS_WEEWX.items()
        }
        self.df.rename(columns=columns, inplace=True)
        self.df.set_index(time, inplace=True)
        self.unit_correction()

    def unit_correction(self):
        """
        Convert to Climate and Forecast standard units.
        """
        self.df[StandardNames.WIND_SPEED.value] = (
            self.df[StandardNames.WIND_SPEED.value]
            * MILES_PER_HOUR_TO_METERS_PER_SECOND
        )
        self.df[StandardNames.WIND_SPEED_OF_GUST.value] = (
            self.df[StandardNames.WIND_SPEED_OF_GUST.value]
            * MILES_PER_HOUR_TO_METERS_PER_SECOND
        )
        self.df[StandardNames.AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.AIR_TEMPERATURE.value] + 459.67) * 5 / 9
        )
        self.df[StandardNames.DEW_POINT_TEMPERATURE.value] = (
            (self.df[StandardNames.DEW_POINT_TEMPERATURE.value] + 459.67) * 5 / 9
        )
        self.df[StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.HEAT_INDEX_OF_AIR_TEMPERATURE.value] + 459.67)
            * 5
            / 9
        )
        self.df[StandardNames.AIR_PRESSURE.value] = (
            self.df[StandardNames.AIR_PRESSURE.value] * INCHES_OF_MERCURY_TO_PASCAL
        )
        self.df[StandardNames.RELATIVE_HUMIDITY.value] = (
            self.df[StandardNames.RELATIVE_HUMIDITY.value] * 0.01
        )
        # density and length units cancel out
        self.df[StandardNames.RAINFALL_AMOUNT.value] = (
            self.df[StandardNames.RAINFALL_AMOUNT.value] * 25.4
        )
        self.df[StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value] = (
            self.df[StandardNames.WATER_EVAPOTRANSPIRATION_FLUX.value] * 25.4 / 3600
        )
        self.df[StandardNames.RAINFALL_RATE.value] = (
            self.df[StandardNames.RAINFALL_RATE.value] * 25.4 / 3600
        )
        self.df[StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value] = (
            (self.df[StandardNames.WIND_CHILL_OF_AIR_TEMPERATURE.value] + 459.67)
            * 5
            / 9
        )
        # none for irradiance, UV


@plot.command(name=ClickCommands.COMPARE.value)
@source_options
@plot_options
# pylint: disable=redefined-builtin
def plot_comparison(
    station: StationName,
    series: StandardNames,
    host: str,
    measurement: str,
    token: str,
    format: ImageFormat,
):
    """
    Plot a comparison of local and InfluxDB data for a specific series.
    """
    remote = WeeWxInfluxArchive(measurement, token, host).df[series.value]
    local = WeatherLinkArchive(station.value).df[series.value]
    start: datetime = local.index.min()
    end: datetime = remote.index.max()
    filename = f"{FIGURES_DIR}/{ClickCommands.COMPARE.value}/{station.value}/{series.value}.{format.value}"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 6))
    freq = "1D"
    daily = local.resample(freq)
    series_max = daily.max()
    color = "black"
    ax = fig.subplots()
    ax.plot(
        series_max.index,
        series_max,
        label=f"{local.name} {freq.lower()} max",
        color=color,
    )
    series_mean = daily.mean()
    plt.plot(
        series_mean.index,
        series_mean,
        label=f"{local.name} {freq.lower()} mean",
        color=color,
        linestyle="--",
    )
    daily = remote.resample(freq)
    series_max = daily.max()
    color = "red"
    plt.plot(
        series_max.index,
        series_max,
        label=f"{remote.name} {freq.lower()} max",
        color=color,
    )
    series_mean = daily.mean()
    plt.plot(
        series_mean.index,
        series_mean,
        label=f"{remote.name} {freq.lower()} mean",
        color=color,
        linestyle="--",
    )
    layout(ax, start, end, ClickCommands.COMPARE, station, series.value, (start, end))
    fig.tight_layout()
    fig.savefig(filename)


@plot.command(name=ClickCommands.TAIL.value)
@source_options
@plot_options
@click.option(
    "--last",
    default="7D",
    help="The time range to include in the plot (e.g., 7D, 14D).",
)
# pylint: disable=redefined-builtin
def plot_tail(
    station: StationName,
    series: StandardNames,
    host: str,
    measurement: str,
    token: str,
    format: ImageFormat,
    last: str,
):
    """
    Plot a comparison of local and InfluxDB data for a specific series.
    """
    remote = WeeWxInfluxArchive(measurement, token, host).df[series.value]
    local = WeatherLinkArchive(station.value).df[series.value]
    filename = f"{FIGURES_DIR}/{ClickCommands.TAIL.value}/{station.value}/{series.value}.{format.value}"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 6))
    ax = fig.subplots()
    tail = local.last(last)
    ax.plot(tail.index, tail, color="black", label="local")
    tail = remote.last(last)
    ax.plot(tail.index, tail, color="red", linestyle="--", label="database")
    start: datetime = local.index.min()
    end: datetime = remote.index.max()
    layout(
        ax,
        start,
        end,
        ClickCommands.TAIL,
        station,
        series.value,
        (tail.index[0], tail.index[-1]),
    )
    fig.tight_layout()
    fig.savefig(filename)


@weather.command(name=ClickCommands.DESCRIBE.value)
@click.argument("name")
def describe(name: str):
    """
    Parse and normalize weather station data for display
    """
    df = WeatherLinkArchive(name).df
    values = CF_STANDARD_NAME_TO_DAVIS_WEEWX.keys()
    ind = df.columns.intersection(values)
    compatible = df[ind]
    print(compatible.describe(include="all"))
    print(compatible.dtypes)


@weather.command(name=ClickCommands.EXPORT.value)
@click.argument("name")
def export(name: str):
    """
    Export normalized weather station data to CSV.
    """
    df = WeatherLinkArchive(name).df
    filename = DATA_DIR / f"{name}.csv"
    df.to_csv(filename)


@weather.command(name=ClickCommands.INFLUX.value)
@source_options
def influx(_: StationName, __: StandardNames, host: str, measurement: str, token: str):
    """
    Show information about the data already stored in Influx database.
    """
    df = WeeWxInfluxArchive(measurement, token, host).df
    print(df.describe(include="all"))
    print(df.dtypes)


def layout(
    ax: Axes,
    start: datetime,
    end: datetime,
    command: ClickCommands,
    station: StationName,
    series: str,
    xlim: tuple[float, float],
):
    """
    Apply standard formatting layout to plots.
    """
    display_name = series.replace("_", " ").title()
    if start.year == end.year:
        year_range = f"{start.year}"
    else:
        year_range = f"{start.year}-{end.year}"
    plt.title(f"{command.value} {station.value} {display_name} {year_range}".title())
    plt.xlabel("Date")
    plt.xticks(rotation=45)
    ax.set_xlim(xlim)
    ax.set_ylim([None, None])
    major_locator = (
        mdates.DateLocator if (end - start).days < 14 else mdates.WeekdayLocator
    )
    ax.xaxis.set_major_locator(major_locator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))  # Customize format
    units = CF_STANDARD_NAME_TO_UNITS.get(series, None)
    if units is not None:
        plt.ylabel(f"{display_name} ({units})")
    else:
        plt.ylabel(display_name)
    plt.legend()


@plot.command(name=ClickCommands.DAILY.value)
@source_options
@plot_options
# pylint: disable=too-many-locals,redefined-builtin
def plot_daily(
    station: StationName,
    series: Enum,
    host: str,
    measurement: str,
    token: str,
    format: ImageFormat,
):
    """
    Display concatenated data, aggregated by day.

    Box plots don't use date axis the same way as line and scatter plots,
    so we have to calculate positions and offsets manually.
    """
    db = WeeWxInfluxArchive(measurement, token, host).df
    local = WeatherLinkArchive(station.value).df
    start: datetime = local.index.min()
    end: datetime = db.index.max()
    key: str = series.value
    filename = f"{FIGURES_DIR}/{ClickCommands.DAILY.value}/{station.value}/{key}.{format.value}"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    df = concat([local[key], db[key]], axis=0)
    fig = plt.figure(figsize=(12, 6))
    ax = fig.subplots()
    grouper = Grouper(freq="D")
    gb = df.groupby(grouper, sort=True)
    groups = gb.groups.keys()
    indices = gb.groups.values()
    epoch = datetime(1970, 1, 1)
    pos = [(group - epoch).days for group in groups]
    bins = []
    previous = 0
    for each in indices:
        bins.append(df[previous:each])
        previous = each
    plt.boxplot(
        bins, notch=False, widths=0.8, positions=pos, medianprops={"color": "black"}
    )
    layout(
        ax, start, end, ClickCommands.DAILY, station, key, (pos[0] - 0.5, pos[-1] + 0.5)
    )
    fig.tight_layout()
    fig.savefig(filename)
    plt.close()


@weather.command(name=ClickCommands.STATS.value)
@source_options
def stats(station: str, series: str, host: str, measurement: str, token: str):
    """
    Compare local and database data before merging or backfilling.
    """
    db = WeeWxInfluxArchive(measurement, token, host).df
    local = WeatherLinkArchive(station).df
    print(f"\nColumn: {series}")
    try:
        series_a = db[series]
        series_a.name = "influx"
        series_b = local[series]
        series_b.name = "local"
        df = concat([series_a, series_b], axis=1)
        print(df.describe(include="all"))
    except (KeyError, ValueError) as e:
        print(f"Error processing column {series}: {e}")


@weather.command(name=ClickCommands.BACKFILL.value)
@source_options
def backfill(
    station: StationName, series: StandardNames, host: str, measurement: str, token: str
):
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

@weather.command(name=ClickCommands.QUALITY.value)
def quality():
    """
    Assess the quality of the weather data.
    """
    pass

@weather.command(name=ClickCommands.DEPLOY.value)
def deploy():
    """
    Deploy the weather application using balena
    """
    balena = Balena()
    api_key = getenv("BALENA_API_KEY", "")
    balena.auth.login_with_token(api_key)
