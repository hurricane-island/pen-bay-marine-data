"""
Command line interfaces for working with vertical profiles of water column data,
such as temperature, salinity, and density.
"""
import click
from enum import Enum
from typing import cast
from pathlib import Path
from pandas import read_csv, DataFrame, Series, cut
from numpy import arange, zeros, arange, ones, array, column_stack, concatenate, meshgrid, linspace, isnan, interp, nan, floor, ceil
from matplotlib.pyplot import subplots, close
from scipy.interpolate import griddata
from gsw import rho
from buoys import haversine

DATA_DIR = Path(__file__).parent / "data"
FIGURES_DIR = Path(__file__).parent / "figures"

class Dimension(Enum):
    """
    Data columns
    """

    DEPTH = "DEP m"
    TEMPERATURE = "°C"
    LATITUDE = "Lat"
    LONGITUDE = "Lon"
    DO_SATURATION = "DO %"
    DO_CONCENTRATION = "DO mg/L"
    SALINITY = "SAL-ppt"
    CHLOROPHYLL = "Chl RFU"
    PYCOERYTHRIN = "BGA-PE RFU"
    DENSITY = "density"
    PRESSURE = "DEP psia"

@click.group()
def profiles():
    """Profile CLI commands."""


@profiles.group()
def plot():
    """Plot CLI commands."""


def load_profile_downcast(filepath: Path, encoding="utf-16"):
    """
    Read the data file and extract relevant information
    Need to get metadata from the fileheader for log interval and site
    """
    skiprows = 0
    with open(filepath, "r", encoding=encoding) as fid:
        while True:
            line = fid.readline()
            if "Date,Time," in line:
                break
            skiprows += 1
    df: DataFrame = read_csv(
        filepath,
        skiprows=skiprows,
        encoding=encoding,
        index_col=False
    )
    df[Dimension.DENSITY.value] = rho(
        df[Dimension.SALINITY.value],
        df[Dimension.TEMPERATURE.value],
        df[Dimension.PRESSURE.value] * 0.689476
    )
    stop = cast(int, df[Dimension.DEPTH.value].idxmax()) + 1
    return df[:stop]


@plot.command(name="single")
@click.argument(
    "filename"
)
@click.option(
    "--dim",
    default=Dimension.TEMPERATURE,
    type=click.Choice(Dimension, case_sensitive=False),
    required=True,
    help="Dimension for analysis.",
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
def profiles_plot_single(filename: str, dim: Dimension, step: float, figsize: tuple) -> None:
    """
    Plot a single depth profile, e.g., temperature, salinity, or density.
    """

    # Need to tell program how to find the data
    filepath: Path = (DATA_DIR / filename).with_suffix(".csv")
    depth_col = "DEP m"

    # Read the data file and extract relevant information
    # Need to get metadata from the fileheader for log interval and site
    skiprows = 0
    interval = 0
    site = ""
    with open(filepath, "r", encoding="utf-16") as fid:
        while True:
            line = fid.readline()
            if "Site:," in line:
                site = line.split(",")[1].strip()
            if "Log Interval:," in line:
                interval = float(line.split(",")[1].strip())
            if "Date,Time," in line:
                break
            skiprows += 1


    df: DataFrame = read_csv(filepath, skiprows=skiprows, encoding='utf-16',index_col=False)
    df[Dimension.DENSITY.value] = rho(
        df[Dimension.SALINITY.value],
        df[Dimension.TEMPERATURE.value],
        df[Dimension.PRESSURE.value] * 0.689476
    )

    max_depth = df[depth_col].max()
    loc_max = df[depth_col].idxmax()
    upcast = df[loc_max+1:-1]
    downcast = df[:loc_max+1]

    start = 0.0
    stop = max_depth + step

    # Create bins and apply pd.cut
    bins = arange(start, stop, step)
    downcast["depth_bin"] = cut(downcast[depth_col], bins=bins)

    # Group by the bins and calculate the average
    resampled_df = downcast.groupby("depth_bin", observed=False)[dim.value].mean().reset_index()
    resampled_df.columns = ["distance_interval", "average_value"]
    depth = [x.left + step/2 for x in resampled_df["distance_interval"]]

    fig, ax = subplots(figsize=figsize)
    ax.plot(resampled_df["average_value"], depth, color="black", zorder=2, label=f"mean ({step} m)")
    ax.scatter(downcast[dim.value], downcast[depth_col], marker="x", color="grey", zorder=1, label="downcast")
    ax.scatter(upcast[dim.value], upcast[depth_col], marker="x", color="pink", zorder=0, label="upcast")
    ax.set_xlabel(dim.value)
    ax.set_ylabel("Depth (m)")
    ax.invert_yaxis()
    ax.set_title(f"{site} {dim.name.lower()} (dt = {interval} s)")
    ax.legend(loc="best")
    
    # Save the figure to the figures directory
    outfile = (FIGURES_DIR / f"{Path(filename).stem}_{dim.name.lower()}").with_suffix('.png')
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches='tight')
    click.echo(f"Figure saved to {outfile}")
    close(fig)

@plot.command("transect")
@click.argument("prefix")
@click.option(
    "--dim",
    default=Dimension.TEMPERATURE,
    type=click.Choice(Dimension, case_sensitive=False),
    required=True,
    help="Dimension for analysis.",
)
@click.option(
    "--levels",
    default=10,
    type=int,
    help="Bins for colormap breaks."
)
def profiles_plot_transect(prefix: str, dim: Dimension, levels=10):
    """
    Create a plot of a transect, with value linearly interpolated between
    sites.
    """
    files = list(DATA_DIR.glob(f"{prefix}*.csv"))
    x = []
    z = []
    h = []
    x_interp = []
    z_max = []
    prev_coords: None | tuple[float, float] = None
    x_sample = 0.0
    for file in sorted(files):
        df = load_profile_downcast(file)
        lat = df[Dimension.LATITUDE.value].mean()
        lon = df[Dimension.LONGITUDE.value].mean()
        if prev_coords is None:
            dx = 0.0
        else:
            dx = haversine(*prev_coords, lon, lat)
        print(x_sample, dx)
        x_sample += dx
        x_interp.append(x_sample)
        prev_coords = (lon, lat)
        count = len(df)
        x.extend([x_sample] * count)
        depth = -df[Dimension.DEPTH.value]
        z.extend(depth.tolist())
        z_max.append(depth.min())
        h.extend(df[dim.value].tolist())

    x = array(x)
    z = array(z)
    h = array(h)
    x_interp = array(x_interp)
    depth_max = array(z_max)

    # Determine the bounds of the transect cross-section
    x_min, x_max = x.min(), x.max()
    z_min, z_max = z.min(), z.max()
    h_min, h_max = h.min(), h.max()

    # Create a structured grid coordinate matrix
    x_pts = linspace(x_min, x_max, 200)
    grid_x, grid_z = meshgrid(
        x_pts,
        linspace(z_min, z_max, 100)
    )
    points_coord = column_stack((x, z))
    grid_v = griddata(
        points=points_coord,
        values=h,
        xi=(grid_x, grid_z),
        method='linear'
    )

    grid_seafloor_profile = interp(grid_x, x_interp, depth_max)
    out_of_bounds_mask = grid_z < grid_seafloor_profile
    grid_v[out_of_bounds_mask] = nan

    fig, ax = subplots(figsize=(10, 6))
    contour = ax.contourf(grid_x, grid_z, grid_v, cmap='cool')
    cbar = fig.colorbar(contour, shrink=0.5)
    cbar.set_label(dim.name.lower())
    ax.scatter(x, z, color='none', edgecolor='black', s=40)
    ax.set_xlabel('distance (m)')
    ax.set_ylabel('depth (m)')
    ax.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f'{prefix}_{dim.name.lower()}_transect.png')
