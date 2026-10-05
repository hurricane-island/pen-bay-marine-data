"""
Command line interfaces for working with vertical profiles of water column data,
such as temperature, salinity, and density.
"""
from enum import StrEnum, auto
import json
from typing import Optional, cast
from pathlib import Path
from click import group, argument, option, Choice, echo
from pandas import read_csv, DataFrame, cut
from numpy import arange, array, column_stack, meshgrid, linspace, interp, nan
from matplotlib.pyplot import subplots, close
from scipy.interpolate import griddata
from pyproj import Transformer
from gsw import rho
from lib import haversine



transformer = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)

DATA_DIR = Path(__file__).parent / "data"
TMP_DIR = Path(__file__).parent / "tmp"
FIGURES_DIR = Path(__file__).parent / "figures"

class Dimension(StrEnum):
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
    DENSITY = auto()
    PRESSURE = "DEP psia"

@group()
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
    df[Dimension.DENSITY] = rho(
        df[Dimension.SALINITY],
        df[Dimension.TEMPERATURE],
        df[Dimension.PRESSURE] * 0.689476
    )
    stop = cast(int, df[Dimension.DEPTH].idxmax()) + 1
    return df[:stop]


@plot.command(name="single")
@argument(
    "filename"
)
@option(
    "--dim",
    default=Dimension.TEMPERATURE,
    type=Choice(Dimension, case_sensitive=False),
    required=True,
    help="Dimension for analysis.",
)
@option(
    "--step",
    default=1.0,
    help="Step size for depth binning.",
    type=float
)
@option(
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
    df[Dimension.DENSITY] = rho(
        df[Dimension.SALINITY],
        df[Dimension.TEMPERATURE],
        df[Dimension.PRESSURE] * 0.689476
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
    resampled_df = downcast.groupby("depth_bin", observed=False)[dim].mean().reset_index()
    resampled_df.columns = ["distance_interval", "average_value"]
    depth = [x.left + step/2 for x in resampled_df["distance_interval"]]

    fig, ax = subplots(figsize=figsize)
    ax.plot(resampled_df["average_value"], depth, color="black", zorder=2, label=f"mean ({step} m)")
    ax.scatter(downcast[dim], downcast[depth_col], marker="x", color="grey", zorder=1, label="downcast")
    ax.scatter(upcast[dim], upcast[depth_col], marker="x", color="pink", zorder=0, label="upcast")
    ax.set_xlabel(dim)
    ax.set_ylabel("Depth (m)")
    ax.invert_yaxis()
    ax.set_title(f"{site} {dim.name.lower()} (dt = {interval} s)")
    ax.legend(loc="best")
    
    # Save the figure to the figures directory
    outfile = (FIGURES_DIR / f"{Path(filename).stem}_{dim.name.lower()}").with_suffix('.png')
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches='tight')
    echo(f"Figure saved to {outfile}")
    close(fig)

@plot.command("transect")
@argument("prefix")
@option(
    "--dim",
    default=Dimension.TEMPERATURE,
    type=Choice(Dimension, case_sensitive=False),
    required=True,
    help="Dimension for analysis.",
)
@option(
    "--levels",
    default=None,
    type=Optional[int],
    help="Bins for colormap breaks."
)
def profiles_plot_transect(prefix: str, dim: Dimension, levels: Optional[int]):
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
        lat = df[Dimension.LATITUDE].mean()
        lon = df[Dimension.LONGITUDE].mean()
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
        depth = -df[Dimension.DEPTH]
        z.extend(depth.tolist())
        z_max.append(depth.min())
        h.extend(df[dim].tolist())

    x = array(x)
    z = array(z)
    h = array(h)
    x_interp = array(x_interp)
    depth_max = array(z_max)

    # Determine the bounds of the transect cross-section
    x_min, x_max = x.min(), x.max()
    z_min, z_max = z.min(), z.max()

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
    contour = ax.contourf(grid_x, grid_z, grid_v, cmap='cool', levels=levels)
    cbar = fig.colorbar(contour, shrink=0.5)
    cbar.set_label(dim.name.lower())
    ax.scatter(x, z, color='none', edgecolor='black', s=40)
    ax.set_xlabel('distance (m)')
    ax.set_ylabel('depth (m)')
    ax.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f'{prefix}_{dim.name.lower()}_transect.png')


@plot.command(name="map")
@argument("prefix")
def profiles_plot_map(prefix: str):
    """
    Create a map
    """
    with open(TMP_DIR / "tide-line.geojson") as f:
        geojson_data = json.load(f)

    fig, ax = subplots(figsize=(3, 6))
    for feature in geojson_data["features"]:
       
        geom_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        print(f"Type: {geom_type}, Coordinates: {len(coordinates)}")
        if geom_type == "LineString":
            x, y = transformer.transform(*zip(*coordinates))
            ax.plot(x, y, color="grey", linewidth=1)
        elif geom_type == "MultiLineString":
            for line in coordinates:
                x, y = transformer.transform(*zip(*line))
                ax.plot(x, y, color="grey", linewidth=1)

    x_lim, y_lim = transformer.transform((-68.9, -68.85), (44.0, 44.1))

    files = list(DATA_DIR.glob(f"{prefix}*.csv"))
    for file in sorted(files):
        df = load_profile_downcast(file)
        lat = df[Dimension.LATITUDE].mean()
        lon = df[Dimension.LONGITUDE].mean()
        x, y = transformer.transform(lon, lat)
        ax.scatter(x, y, color="black", s=40)

    lx, ly = transformer.transform((-68.887828, -68.871323), (44.044788, 44.031605))
    ax.scatter(lx, ly, color="red", s=40)
    bx, by = transformer.transform(-68.89224, 44.04357)
    ax.scatter(bx, by, color="blue", s=40)

    ax.set_title("Map")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)
    ax.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / 'map.png', bbox_inches='tight', dpi=300)