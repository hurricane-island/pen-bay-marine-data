"""
Add cable related commands here, specific to buoys, and usually the
only case of using geospatial information in this module, except for QA.
"""

from enum import StrEnum, auto
from typing import Optional, cast
from pathlib import Path
from datetime import datetime
from click import group, option, DateTime, ClickException, echo, FloatRange, IntRange
from pandas import DataFrame
from numpy import array, concatenate
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
from matplotlib.markers import MarkerStyle
from scipy.io import loadmat
from gpxpy.gpx import GPX, GPXTrack, GPXTrackSegment, GPXTrackPoint, Tuple

from lib.geo import to_utm
from buoys.options import (
    StationName,
    TableName,
    VendoredNames,
    station_name,
    read_campbell_logger_files,
    filter_buoy_flat_files,
    FIGURES_DIR,
    FEATURES_OF_INTEREST,
    DATA_DIR,
    EXPORT_DIR,
)


class ClickOptions(StrEnum):
    """
    Available commands for buoy moorings and cables.
    """

    LOCATIONS = auto()
    # plot
    PLOT = auto()
    PREDICT = auto()
    MAP = auto()
    # export
    EXPORT = auto()
    GPX = auto()


@group(name=ClickOptions.LOCATIONS)
def locations():
    """
    Work with buoy location to assess mooring performance.
    """


@group(name=ClickOptions.PLOT)
def plot():
    """
    Visualize buoy location data.
    """


@group(name=ClickOptions.EXPORT)
def export():
    """
    Export buoy location data for use in other programs.
    """


def resolve_column(df: DataFrame, name: VendoredNames) -> tuple:
    """
    Resolve a vendored variable name to the fully-qualified column label. The raw
    Campbell logger files are read with a three level header (name, units,
    aggregation), so a bare name is only a partial key and is rejected as
    non-unique by operations like `sort_values`.
    """
    matches = [col for col in df.columns if isinstance(col, tuple) and col[0] == name]
    if not matches:
        raise ValueError(f"No column found for {name}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous column {name}, matched {len(matches)}: {matches}")
    return matches[0]


def df_to_gpx_xml(df: DataFrame, lon: Tuple[str, ...], lat: Tuple[str, ...]) -> str:
    """
    Convert a DataFrame with latitude and longitude columns to a GPX XML string.
    """
    gpx = GPX()

    # Create first track in our GPX:
    gpx_track = GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for time, row in df.iterrows():
        point = GPXTrackPoint(
            row[lat], row[lon], elevation=0, time=cast(datetime, time)
        )
        gpx_segment.points.append(point)
    return gpx.to_xml()


def predicted_watch_circle(
    center_xy: tuple[float, float],
    station: StationName,
    color: str,
    scale: float = 1.0,
    label: str | None = None,
) -> list[Circle]:
    """
    Generate a predicted watch circle based on the planned deployment location.
    """
    predicted: list[Circle] = []
    for each, circle_label, ls in [("low", label, "solid"), ("high", None, "dashed")]:
        mat_path = DATA_DIR / f"{station}-{each}.mat"
        if not mat_path.exists():
            raise FileNotFoundError(f"Missing cable simulation file: {mat_path}")
        data = loadmat(mat_path)
        radius = float(data["x"].max()) * scale
        predicted.append(
            Circle(
                center_xy,
                radius=radius,
                color=color,
                fill=False,
                linestyle=ls,
                label=circle_label,
            )
        )
    return predicted


def date_range_options(function):
    """
    Add start and end date options to a Click command.
    """
    function = option(
        "--start",
        default=None,
        type=DateTime(formats=["%Y-%m-%d"]),
        help="Optional start date for filtering data.",
    )(function)
    function = option(
        "--end",
        default=None,
        type=DateTime(formats=["%Y-%m-%d"]),
        help="Optional end date for filtering data.",
    )(function)
    return function


@export.command(name=ClickOptions.GPX)
@station_name
@option(
    "--tail",
    default=24,
    type=IntRange(min=1, max=24*30),
    help="Number of most recent records to include in the GPX export.",
)
def buoys_locations_export_gpx(name: StationName, tail: int):
    """
    Export buoy data to a different format.
    """
    table = TableName.DIAGNOSTIC
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(list(files))
    mask = ~df.index.duplicated(keep=False)
    unique = df[mask].sort_index()
    unique.index.rename("time", inplace=True)
    gpx = df_to_gpx_xml(
        unique.tail(tail),
        lon=resolve_column(df, VendoredNames.LONGITUDE),
        lat=resolve_column(df, VendoredNames.LATITUDE),
    )
    path = (EXPORT_DIR / name).with_suffix(".gpx")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fid:
        fid.write(gpx)
    echo(f"GPX file written to {path}")


@plot.command(name=ClickOptions.LOCATIONS)
@station_name
@date_range_options
@option(
    "--distance",
    required=True,
    default=100.0,
    type=Optional[FloatRange(min=0.0, max=1000.0)],
    help="filter GPS points by distance from planned deployment location (meters)",
)
@option(
    "--satellites",
    required=True,
    type=IntRange(min=4, max=10),
    help="minimum number of satellites",
    default=4,
)
@option(
    "--cable",
    is_flag=True,
    help="include predicted watch circle from WHOI cable simulation",
)
def buoys_locations_plot_map(
    name: StationName,
    distance: Optional[float],
    satellites: int,
    start: Optional[datetime],
    end: Optional[datetime],
    cable: bool,
):
    """
    Plot the lat and long of the buoy hourly over the course of the deployment period.
    This only uses historical data contained in local raw files. Compare it to the
    deployment location of the anchor and the watch circle predicted by WHOI Cable
    simulations.
    """
    table = TableName.DIAGNOSTIC
    planned = FEATURES_OF_INTEREST[name].feature.coordinates
    files = filter_buoy_flat_files(name, table)
    df = read_campbell_logger_files(list(files))
    satellites_column = resolve_column(df, VendoredNames.SATELLITES_IN_VIEW)
    latitude_column = resolve_column(df, VendoredNames.LATITUDE)
    longitude_column = resolve_column(df, VendoredNames.LONGITUDE)
    # Sort ascending so that the highest quality fixes are drawn last, on top
    df = df.sort_values(by=satellites_column)
    lat = df[latitude_column]
    lon = df[longitude_column]
    satellite_count = df[satellites_column]
    px, py = to_utm(*planned)
    xx, yy = to_utm(lon, lat)

    mask = array(satellite_count >= satellites)
    dxy = array(((xx - px) ** 2 + (yy - py) ** 2) ** 0.5)
    mask &= dxy < distance
    if start is not None:
        mask &= df.index >= start
    if end is not None:
        mask &= df.index <= end
    if not mask.any():
        raise ClickException(
            "No GPS points remain after filtering; try increasing --distance, lowering --satellites, or adjusting the date filter."
        )

    fig, ax = plt.subplots(figsize=(3, 4))
    sats = array(satellite_count.values[mask])
    time = df.index[mask]
    alpha = (time - time.min()).total_seconds() / (
        time.max() - time.min()
    ).total_seconds()

    handle = ax.scatter(
        xx[mask],
        yy[mask],
        alpha=alpha**4,
        marker=MarkerStyle("o"),
        s=10,
        c=sats,
        edgecolors="none",
        cmap="spring",
        label="Location",
    )
    fig.colorbar(handle, label="Satellites", shrink=0.5)

    if cable:
        planned_xy = predicted_watch_circle((px, py), name, "grey", label="Planned")
        corrected_xy = predicted_watch_circle(
            (0.0, 0.0), name, "black", label="Deployed"
        )
        for patch in planned_xy + corrected_xy:
            ax.add_patch(patch)

    ax.set_ylabel("UTM Northing Δ (m)")
    ax.set_xlabel("UTM Easting Δ (m)")
    ax.set_aspect(1.0)
    ax.set_title(f"N = {len(sats)}")

    filename = FIGURES_DIR / "locations" / name / "watch-circle.png"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    ax.ticklabel_format(axis="both", style="plain")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(filename, dpi=300, bbox_inches="tight")
    echo(f"Saved to {filename}")


@plot.command(name=ClickOptions.PREDICT)
@station_name
def buoys_locations_plot_predict(name: StationName):
    """
    Plot the mooring tension diagram from the WHOI cable simulation.
    """
    low = DATA_DIR / f"{name}-low.mat"
    high = DATA_DIR / f"{name}-high.mat"
    if not low.exists() or not high.exists():
        raise ValueError(
            f"Missing cable simulation .mat files for station '{name}' (expected {low.name} and {high.name} under {DATA_DIR})"
        )
    low_data = loadmat(low)
    high_data = loadmat(high)
    fig, ax = plt.subplots(figsize=(4, 3))
    x = concatenate([low_data["x"], high_data["x"]])
    y = concatenate([low_data["z"], high_data["z"]])
    z = concatenate([low_data["T"], high_data["T"]])
    handle = ax.scatter(x, y, c=z, s=2, cmap="spring", label="Mooring")
    ax.vlines(
        low_data["x"].max(),
        ymin=0.0,
        ymax=low_data["z"].max(),
        colors="black",
        linestyles="solid",
        label="Low Tide",
    )
    ax.vlines(
        high_data["x"].max(),
        ymin=0.0,
        ymax=high_data["z"].max(),
        colors="black",
        linestyles="dashed",
        label="High Tide",
    )
    ax.hlines(
        high_data["depth"],
        xmin=0.0,
        xmax=high_data["x"].max(),
        colors="black",
        linestyles="dashed",
    )
    ax.hlines(
        low_data["depth"],
        xmin=0.0,
        xmax=low_data["x"].max(),
        colors="black",
        linestyles="solid",
    )
    ax.set_aspect(1.0)
    fig.colorbar(handle, label="Tension (N)", shrink=0.5)
    ax.set_ylim(y.min(), None)
    ax.set_xlim(x.min(), None)
    ax.set_xlabel("Displacement (m)")
    ax.set_ylabel("Water Level (m)")
    ax.legend(loc="best")
    filename = FIGURES_DIR / "moorings" / name / "mooring-tension.png"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(filename, bbox_inches="tight", dpi=300)
    echo(f"Saved to {filename}")
