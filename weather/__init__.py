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
import click
from pandas import read_csv, to_datetime, DataFrame, Series, concat, Grouper
from influxdb_client_3 import InfluxDBClient3
from os import getenv
from matplotlib import pyplot as plt, dates as mdates
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"
TIME = "time"
# Unique to WeeWx, either derived or a bookkeeping convenience
weewx_derived = {
    "altimeter",  # float64
    "appTemp",  # float64
    "binding",  # object
    "cloudbase",  # float64
    "consBatteryVoltage",  # float64
    "dayET",  # float64
    "dayRain",  # float64
    "extraAlarm1",  # float64
    "extraAlarm2",  # float64
    "extraAlarm3",  # float64
    "extraAlarm4",  # float64
    "extraAlarm5",  # float64
    "extraAlarm6",  # float64
    "extraAlarm7",  # float64
    "extraAlarm8",  # float64
    "forecastIcon",  # float64
    "forecastRule",  # float64
    "insideAlarm",  # float64
    "maxSolarRad",  # float64
    "monthET",  # float64
    "monthRain",  # float64
    "outsideAlarm1",  # float64
    "outsideAlarm2",  # float64
    "pressure",  # float64
    "rainAlarm",  # float64
    "soilLeafAlarm1",  # float64
    "soilLeafAlarm2",  # float64
    "soilLeafAlarm3",  # float64
    "soilLeafAlarm4",  # float64
    "stormRain",  # float64
    "stormStart",  # float64
    "sunrise",  # float64
    "sunset",  # float64
    "txBatteryStatus",  # float64
    "usUnits",  # float64
    "windSpeed10",  # float64
    "yearET",  # float64
    "yearRain",  # float64
}
# Weather Link to WeeWx mapping
NAME_LOOKUP = {
    "Temp Out": "outTemp",
    "Hi Temp": "highOutTemp",
    "Low Temp": "lowOutTemp",
    "Out Hum": "outHumidity",
    "Dew Pt.": "dewpoint",
    "Wind Speed": "windSpeed",
    "Wind Dir": "windDir",
    "Wind Run": "windrun",
    "Hi Speed": "windGust",
    "Hi Dir": "windGustDir",
    "Wind Chill": "windchill",  # float64
    "Heat Index": "heatindex",  # float64
    "THW Index": "humindex",  # float64
    "THSW Index": None,  # float64
    "Bar": "barometer",  # float64
    "Rain": "rain",  # float64
    "Rain Rate": "rainRate",  # float64
    "Solar Rad.": "radiation",  # float64
    "Solar Energy": None,  # float64
    "Hi Solar Rad.": "highRadiation",  # float64
    "UV Index": "UV",  # float64
    "UV Dose": None,  # float64
    "Hi UV": "highUV",  # float64
    "Heat D-D": None,  # float64
    "Cool D-D": None,  # float64
    "In Temp": "inTemp",
    "In Hum": "inHumidity",
    "In Dew": "inDewpoint",  # float64
    "In Heat": None,  # float64
    "In EMC": None,  # float64
    "In Air Density": None,  # float64
    "ET": "ET",  # float64
    "Wind Samp": "wind_samples",  # float64
    "Wind Tx": None,  # int64
    "ISS Recept": "rxCheckPercent",  # float64
    "Arc. Int.": "interval",  # int64
}


@click.group()
def weather():
    """
    Weather data tools.
    """


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
        for items in zip(*rows):
            header = ""
            for each in items:
                header += str(each).strip() + " "
            header = header.strip()
            if header in NAME_LOOKUP and NAME_LOOKUP[header] is not None:
                header = NAME_LOOKUP[header]
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
        df.drop(columns=[date, time])
        self.df = df

    def __repr__(self):
        return f"Archive(name={self.name})"


def get_influx_data(
    measurement: str, time: str = TIME, database: str = "weather"
) -> DataFrame:
    """
    Get data from InfluxDB and format as a DataFrame.
    """
    token = getenv("INFLUX_API_TOKEN", "")
    host = getenv("INFLUX_SERVER_URL", "")
    client = InfluxDBClient3(host=host, database=database, token=token)
    df: DataFrame = client.query(
        f"SELECT * FROM {measurement} WHERE binding IN ('archive') ORDER BY {time}",
        mode="pandas",
    )
    return df.set_index(time)


def resample_series(
    series: Series, freq: str = "1D", color: str = "black"
) -> DataFrame:
    """
    Resample a time series to a specified frequency.
    """
    daily = series.resample(freq)
    series_max = daily.max()
    plt.plot(
        series_max.index,
        series_max,
        label=f"{series.name} {freq.lower()} max",
        color=color,
    )
    series_mean = daily.mean()
    plt.plot(
        series_mean.index,
        series_mean,
        label=f"{series.name} {freq.lower()} mean",
        color=color,
        linestyle="--",
    )


@weather.command(name="plot")
@click.argument("station")
@click.argument("series")
@click.option("--measurement", default="observations", help="The InfluxDB measurement (table) name.")
def plot_comparison(station: str, measurement: str, series: str):
    """
    Plot a comparison of local and InfluxDB data for a specific series.
    """
    remote = get_influx_data(measurement)[series]
    local = WeatherLinkArchive(station).df[series]
    values = set(NAME_LOOKUP.values())
    values.discard(None)
    if series not in values:
        raise ValueError(f"Series '{series}' is not a valid column: {values}.")
    plt.figure(figsize=(12, 6))
    resample_series(local, color="black")
    resample_series(remote, color="red")
    plt.title(f"Comparison of {series}")
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend()
    plt.savefig(f"{FIGURES_DIR}/comparison_{series}.png")
    plt.close()


@weather.command()
@click.argument("name")
def describe(name: str):
    """
    Parse and normalize weather station data for display
    """
    df = WeatherLinkArchive(name).df
    values = NAME_LOOKUP.values()
    ind = df.columns.intersection(values)
    compatible = df[ind]
    print(compatible.describe(include="all"))
    print(compatible.dtypes)


@weather.command()
@click.argument("name")
def export(name: str):
    """
    Export normalized weather station data to CSV.
    """
    df = WeatherLinkArchive(name).df
    filename = DATA_DIR / f"{name}.csv"
    df.to_csv(filename)


@weather.command()
@click.option(
    "--measurement", default="observations", help="The Influx measurement (table)."
)
def influx(measurement: str):
    """
    Show information about the data already stored in Influx database.
    """
    df = get_influx_data(measurement)
    print(df.describe(include="all"))
    print(df.dtypes)


@weather.command()
@click.argument("station")
@click.argument("series")
@click.option(
    "--measurement",
    default="observations",
    help="The InfluxDB measurement (table) name.",
)
# pylint: disable=too-many-locals
def boxplot(station: str, series: str, measurement: str):
    """
    Display concatenated data, aggregated by day. Boxplots don't use date axis the
    same way as line and scatter plots, so we have to calculate positions and offsets
    manually.
    """
    db = get_influx_data(measurement)
    local = WeatherLinkArchive(station).df
    values = set(NAME_LOOKUP.values())
    values.discard(None)
    if series not in values:
        raise ValueError(f"Series '{series}' is not a valid column: {values}.")
    df = concat([local[series], db[series]], axis=0)
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
        bins, notch=False, widths=0.6, positions=pos, medianprops={"color": "black"}
    )
    plt.title(f"Daily {series}")
    plt.xlabel("date")
    plt.xticks(rotation=45)
    ax.set_xlim([pos[0] - 0.5, pos[-1] + 0.5])
    ax.set_ylim([0, None])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))  # Customize format
    fig.autofmt_xdate()  # Automatically formats and rotates date labels
    plt.ylabel(series)
    plt.savefig(f"{FIGURES_DIR}/aggregation_{series}.png")
    plt.close()


@weather.command()
@click.argument("station")
@click.argument("series")
@click.option(
    "--measurement",
    default="observations",
    help="The InfluxDB measurement (table) name.",
)
def compare(station: str, series: str, measurement: str):
    """
    Compare local and database data before merging or backfilling.
    """
    db = get_influx_data(measurement)
    local = WeatherLinkArchive(station).df
    values = set(NAME_LOOKUP.values())
    values.discard(None)
    if series not in values:
        raise ValueError(f"Series '{series}' is not a valid column: {values}.")
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
