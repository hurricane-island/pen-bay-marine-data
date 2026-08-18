"""
Command line interfaces for working with vertical profiles of water column data,
such as temperature, salinity, and density.
"""
import click
from pathlib import Path
from pandas import read_csv, DataFrame, Series, cut
from numpy import arange
from matplotlib.pyplot import subplots

DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"


@click.group()
def profiles():
    """Profile CLI commands."""


@profiles.group()
def plot():
    """Plot CLI commands."""


@plot.command(name="single")
@click.argument(
    "filename"
)
@click.option(
    "--step",
    default=1.0,
    help="Step size for depth binning.",
    type=float
)
@click.option(
    "--figsize",
    default=(3, 4),
    help="Figure size as a tuple (width, height).",
    type=(float, float)
)
def profiles_plot(filename: str, step: float, figsize: tuple) -> None:
    """
    Plot a single depth profile, e.g., temperature, salinity, or density.
    """

    # Need to tell program how to find the data 
    filename: Path = (DATA_DIR / filename).with_suffix(".csv")
    depth_col = "DEP m"
    temp_col = "°C"

    # Read the data file and extract relevant information
    # Need to get metadata from the fileheader for log interval and site
    skiprows = 0
    interval = 0
    site = ""
    with open(filename, "r", encoding="utf-16") as fid:
        while True:
            line = fid.readline()
            if "Site:," in line:
                site = line.split(",")[1].strip()
            if "Log Interval:," in line:
                interval = float(line.split(",")[1].strip())
            if "Date,Time," in line:
                break
            skiprows += 1


    df: DataFrame = read_csv(filename, skiprows=skiprows, encoding='utf-16',index_col=False)

    max_depth = df[depth_col].max()
    loc_max = df[depth_col].idxmax()
    upcast = df[loc_max+1:-1]
    df = df[:loc_max+1]

    start = 0.0
    stop = max_depth + step

    # Create bins and apply pd.cut
    bins = arange(start, stop, step)
    df["depth_bin"] = cut(df[depth_col], bins=bins)

    # Group by the bins and calculate the average
    resampled_df = df.groupby("depth_bin", observed=False)[temp_col].mean().reset_index()
    resampled_df.columns = ["distance_interval", "average_value"]
    depth = [x.left + step/2 for x in resampled_df["distance_interval"]]

    fig, ax = subplots(figsize=figsize)
    ax.plot(resampled_df["average_value"], depth, color="black", zorder=2, label=f"mean ({step} m)")
    ax.scatter(df[temp_col], df[depth_col], marker="x", color="grey", zorder=1, label="downcast")
    ax.scatter(upcast[temp_col], upcast[depth_col], marker="x", color="pink", zorder=0, label="upcast")
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Depth (m)")
    ax.invert_yaxis()
    ax.set_title(f"{site} Temperature Profile (dt = {interval} s)")
    ax.legend(loc="best")
    
    # Save the figure to the figures directory
    outfile = (FIGURES_DIR / f"{filename.stem}").with_suffix('.png')
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches='tight')
    click.echo(f"Figure saved to {outfile}")

