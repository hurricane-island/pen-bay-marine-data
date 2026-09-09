from click import argument, group, echo
from typing import cast
from matplotlib.dates import DateFormatter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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

@plot.command()
def loggers():
    """
    Plot logger data
    """
    dim = Dimension.TEMPERATURE
    after = datetime(2026, 8, 20)
    date_col = "ISO 8601 Time"
    loggers = ["2503604", "2305707"]
    labels = ["Green's (SE)", "Hurricane (NW)"]
    colors = ["grey", "red"]
    fig, ax = subplots(figsize=(10, 4))
    for serial_number, color, label in zip(loggers, colors, labels):
        files = DATA.glob(f"{serial_number}*.csv")
        frames = []
        for file in files:
            _df = read_csv(file, index_col=date_col, parse_dates=[date_col])
            frames.append(_df)
        df = cast(DataFrame, concat(frames)).sort_index()
        df.index = df.index.tz_localize(None)
        df = df[df.index > after]
        ax.plot(df.index, df[dim.value], color=color, label=label, linewidth=1)
    ax.set_title(f"Lobster Trap Sensors - {dim.value}")
    ax.set_xlabel(Dimension.TIME.value)
    date_form = DateFormatter("%m-%d")
    ax.xaxis.set_major_formatter(date_form)
    ax.set_ylabel(dim.value)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES / f"{dim.name.lower()}.png", bbox_inches="tight", dpi=300)
