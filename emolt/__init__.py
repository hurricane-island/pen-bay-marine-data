from click import argument, group, echo, option, Choice
from typing import cast
from matplotlib.dates import DateFormatter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from io import StringIO
from matplotlib.pyplot import subplots
from pandas import DataFrame, concat, read_csv

FIGURES = Path(__file__).parent / "figures"
DATA = Path(__file__).parent / "data" 
FIGURES.mkdir(exist_ok=True)

class Dimension(Enum):
    """
    Dimensions for logger data columns.
    """

    TIME = "ISO 8601 Time"
    DO_CONCENTRATION = "Dissolved Oxygen (mg/l)"
    DO_SATURATION = "Dissolved Oxygen (%)"
    TEMPERATURE = "DO Temperature (C)"
    WATER_DETECT = "Water Detect (%)"

@group()
def emolt():
    """
    Command Line Interface group for Lobster Trap sensors.
    """

@emolt.group()
def plot():
    """
    Plot data
    """

@plot.command("loggers")
@argument(
    "dim",
    type=Choice(Dimension, case_sensitive=False)
)
def loggers(dim: Dimension):
    """
    Plot logger data
    """
    after = datetime(2026, 8, 25)
    before = datetime(2026, 8, 27)
    date_col = "ISO 8601 Time"
    loggers = ["2503604", "2305707"]
    labels = ["Green's (SE)", "Hurricane (NW)"]
    colors = ["grey", "red"]
    fig, ax = subplots(figsize=(10, 3))
    for serial_number, color, label in zip(loggers, colors, labels):
        files = DATA.glob(f"{serial_number}*.csv")
        frames = []
        for file in files:
            _df = read_csv(file, index_col=date_col, parse_dates=[date_col])
            frames.append(_df)
        df = cast(DataFrame, concat(frames)).sort_index()
        df.index = df.index.tz_localize(None)
        df = df[(df.index > after) & (df.index < before)]
        ax.plot(df.index, df[dim.value], color=color, label=label, linewidth=1)
    ax.set_title(f"Lobster Trap Sensors - {dim.value}")
    ax.set_xlabel(Dimension.TIME.value)
    date_form = DateFormatter("%m-%d %H:%M")
    ax.xaxis.set_major_formatter(date_form)
    ax.set_ylabel(dim.value)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES / f"{dim.name.lower()}.png", bbox_inches="tight", dpi=300)

@plot.command("acoustic-release")
def acoustic_release():
    """
    Plot acoustic release data
    """
    after = datetime(2026, 8, 24)
    before = datetime(2026, 8, 26)
    date_col = "Device Time (UTC)"
    temp_col = "Ambient (deg C)"
    fig, ax = subplots(figsize=(10, 3))
    files = DATA.glob(f"VR2AR*.csv")
    str_data = ""
    for file in files:
        with open(file, encoding="utf-8") as fid:
            for line in fid.readlines():
                if "TEMP_DESC," in line:
                    str_data += line
                elif "TEMP," in line:
                    str_data += line
        df = read_csv(StringIO(str_data), index_col=date_col, parse_dates=[date_col])

    df.index = df.index.tz_localize(None)
    df = df[(df.index > after) & (df.index < before)]
    ax.plot(df.index, df[temp_col], color="black", label="Temperature", linewidth=1)
    ax.set_title(f"Acoustic Release Sensors")
    ax.set_xlabel(Dimension.TIME.value)
    date_form = DateFormatter("%m-%d")
    ax.xaxis.set_major_formatter(date_form)
    ax.set_ylabel("Temp deg C")
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES / f"release_temperature.png", bbox_inches="tight", dpi=300)
