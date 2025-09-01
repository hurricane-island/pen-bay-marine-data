"""
Shared across sensing platforms and systems. Mostly related
to processing Pandas DataFrames and plotting with Matplotlib.
"""

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from matplotlib import pyplot as plt, dates as mdates
from matplotlib.axes import Axes
from click import Choice, option
from pandas import DataFrame, Grouper, Series, concat
from ioos_qc.config import Config
from ioos_qc.streams import PandasStream
from ioos_qc.stores import PandasStore


class ImageFormat(Enum):
    """
    Valid image file formats for writing figures.
    Add values if there is a need, but Portable
    Network Graphics is often a good choice for
    web because of its lossless compression and
    wide support across browsers.
    """

    PNG = "png"

class StandardUnits(Enum):
    """
    CF Metadata Standard Units. These are all of the Davis Vantage Pro2
    observed properties that have Climate and Forecast (CF) metadata standard
    units.
    """

    TEMPERATURE = "deg K"
    PRESSURE = "Pa"
    SPEED = "m/s"
    DIRECTION = "degrees"
    ENERGY = "W/m^2"
    FLUX = "kg/m^2/s"
    AMOUNT = "kg/m^2"


def influx_options(function):
    """
    Attach common options to source commands. When used as
    a decorator, the arguments and options will be supplied
    to the wrapped function in reverse order.
    """
    function = option(
        "--token",
        envvar="INFLUX_API_TOKEN",
        help="The InfluxDB API token. Defaults to environment variable INFLUX_API_TOKEN",
    )(function)
    function = option(
        "--measurement",
        default="observations",
        help="The InfluxDB measurement (table) name.",
    )(function)
    function = option(
        "--host",
        envvar="INFLUX_SERVER_URL",
        help="The InfluxDB server URL. Defaults to environment variable INFLUX_SERVER_URL",
    )(function)
    return function


def plot_options(function):
    """
    Attach common options to plotting commands.
    """
    function = option(
        "--image-format",
        type=Choice(ImageFormat, case_sensitive=False),
        default=ImageFormat.PNG,
        help="The output format.",
    )(function)
    return function


def fahrenheit_to_kelvin(fahrenheit: float) -> float:
    """
    Convert Fahrenheit to Kelvin.
    """
    return (fahrenheit - 32) * 5 / 9 + 273.15


def test_observed_property(
    result: DataFrame, observed_property: str, tests: list[str]
) -> DataFrame:
    """
    Get quality assurance flags for observed property.
    """
    columns = {
        f"{observed_property}_qartod_{test}": test.replace("_test", "")
        for test in tests
    }
    df = result[columns.keys()].rename(columns=columns)
    df["rollup"] = df.max(axis=1).astype("object")
    for col in df.columns:
        df[col] = df[col].astype("object")
    df["observed_property"] = observed_property
    return df


def test_data_frame(df: DataFrame, config: Config, time_column: str) -> DataFrame:
    """
    Apply any necessary processing to the DataFrame
    """
    flags = PandasStream(df).run(config)
    store = PandasStore(flags)
    result = store.save().set_index(time_column)
    frames: dict[str, list[str]] = {}
    for test in result.columns:
        _series, name = test.split("_qartod_")
        if _series not in frames:
            frames[_series] = []
        frames[_series].append(name)

    by_observed_property = []
    for items in frames.items():
        df = test_observed_property(result, *items)
        by_observed_property.append(df)
    return concat(by_observed_property, axis=0)


def cardinal_direction_to_degrees(series: Series) -> Series:
    """
    Convert cardinal directions to degrees.
    """
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
    return series.map(wind)


def plot_single_series(series: Series, ax: Axes, resample: str, label: str, **kwargs):
    """
    Plot a single resampled time series.
    """
    observed_property: str = series.name
    observed_property = observed_property.replace("_", " ").title()
    resampled = series.resample(resample)
    series_mean = resampled.mean()
    ax.plot(series_mean.index, series_mean, label=f"{label} {resample} mean", **kwargs)


def plot_tail(
    local: Series,
    remote: Series,
    thing: str,
    observed_property: str,
    prefix: str,
    units: str = None,
    image_format: ImageFormat = ImageFormat.PNG,
    days: int = 30,
    resample: str = "1h",
    qartod: str = None,
    figsize: tuple[int, int] = (12, 6),
    time_column: str = "time"
):
    """
    Plot the tail of a time series which has some values
    stored locally in a file, and some from a database.
    The local and remote data may overlap, but the local
    is assumed to cover an earlier time interval than
    the remote.
    """
    end: datetime = datetime.now()
    start: datetime = end - timedelta(days=days)
    fig, ax = plt.subplots(figsize=figsize)
    tail = local.loc[local.index > start]
    if qartod is not None:
        config = Config(qartod)
        print(tail.columns)
        qa = test_data_frame(tail.reset_index(), config, time_column='time')
        gb = qa.groupby("observed_property").get_group(observed_property)
        flagged = gb[gb["rollup"] != 1]
        print("Flagged:", len(flagged))

    plot_single_series(
        local.loc[local.index > start], ax, resample, label="file", color="black"
    )
    plot_single_series(
        remote.loc[remote.index > start],
        ax,
        resample,
        label="influx",
        color="red",
        linestyle="--",
    )
    display_name = observed_property.replace("_", " ").title()
    if start.year == end.year:
        year_range = f"{start.year}"
    else:
        year_range = f"{start.year}-{end.year}"
    plt.title(f"{thing} {display_name} {year_range}".title())
    ax.set_xlabel("Date")
    plt.xticks(rotation=45)
    ax.set_xlim(start, end)
    ax.set_ylim(None, None)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=(days // 8) + 2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))  # Customize format
    if units is not None:
        ax.set_ylabel(f"{display_name} ({units})")
    else:
        ax.set_ylabel(display_name)
    ax.legend()
    fig.tight_layout()
    filename = f"{prefix}/{thing}/{observed_property}.{image_format.value}"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filename)


def group_observations_by_time(
    df: DataFrame, freq: str = "D"
) -> tuple[list[DataFrame], list[int]]:
    """
    Group observations by a specified frequency.
    """
    grouper = Grouper(freq=freq)
    gb = df.groupby(grouper, sort=True)
    groups: list[datetime] = list(gb.groups.keys())
    epoch = datetime(1970, 1, 1)
    positions = [(group - epoch).days for group in groups]
    bins = []
    previous = 0
    for each in gb.groups.values():
        bins.append(df[previous:each])
        previous = each
    years = f"{groups[0].year}"
    if groups[0].year != groups[-1].year:
        years += f"-{groups[-1].year}"
    return bins, positions, years

def describe_data_frame(df: DataFrame, config_path: str):
    """
    Display a summary of the DataFrame without an overwhelming amount of detail.
    """
    summary = df.describe().T.drop(columns=["25%", "50%", "75%", "std", "mean"])
    print("\nSamples:\n")
    print(summary)
    config = Config(config_path)
    qa = test_data_frame(df.reset_index(), config, time_column='time')
    gb = qa.groupby("observed_property")
    print("\nQuality Assurance Flags:\n")
    group_summary = gb.describe().T
    print(group_summary)

def boxplot(
    df: DataFrame,
    thing: str,
    observed_property: str,
    prefix: str,
    units: str,
    image_format: ImageFormat = ImageFormat.PNG,
    freq: str = "D",
    figsize: tuple[int, int] = (12, 6),
    tick_interval: int = 5,
    rotation: float = 45,
):
    """
    Create a box plot of a single series grouped
    by time window.
    """
    filename = f"{prefix}/{thing}/{observed_property}.{image_format.value}"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=figsize)
    bins, positions, years = group_observations_by_time(df, freq=freq)
    ax.boxplot(
        bins,
        notch=False,
        widths=0.8,
        positions=positions,
        medianprops={"color": "black"},
    )
    display_name = observed_property.replace("_", " ").title()
    title = f"{thing} {display_name} {years}".title()
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_xlim((positions[0] - 0.5, positions[-1] + 0.5))
    ax.set_ylim((None, None))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=tick_interval))
    plt.xticks(rotation=rotation)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))  # e.g. Dec 10
    if units is not None:
        display_name += f" ({units})"  # note: overloading display_name
    ax.set_ylabel(display_name)
    fig.tight_layout()
    fig.savefig(filename)
