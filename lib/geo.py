"""
Geospatial and mapping utilities for plotting geographic data on a map.
"""

from datetime import datetime
from enum import Enum
from typing import cast, Optional
from math import radians, sin, cos, atan2, sqrt
from pathlib import Path
from matplotlib.patches import Circle
from numpy import array
from numpy.typing import NDArray
from matplotlib.pyplot import Axes
from pandas import DataFrame
from pydantic import BaseModel
from pyproj import Transformer
from gpxpy.gpx import GPX, GPXTrack, GPXTrackSegment, GPXTrackPoint, Tuple
from geojson_pydantic import (
    FeatureCollection,
    Feature,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    Point
)
from geojson_pydantic.types import Position2D

TMP_DIR = Path(__file__).parent.parent / "tmp"
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)

class FeatureOfInterest():
    """
    Features of interest can be:
    - Planned/deployed sensor locations
    - Areas of environmental interest
    """
    name: str
    description: str
    encoding_type: str
    feature: Point

    _utm: None

    def __init__(
        self,
        name: str,
        longitude: float,
        latitude: float,
        description: str = "",
    ):
        self.name = name
        self.description = description
        self.encoding_type = "vendor/vnd.geo+json"
        self.feature = Point(
            type="Point",
            coordinates=Position2D(longitude, latitude)
        )

    def utm_watch_circle(
        self,
        radius: float,
        label: str,
        linestyle: str="solid",
        color: str="black",
    ) -> Circle:
        """
        Create a circular patch representing the watch area around the feature.
        """
        return Circle(
            to_utm(*self.feature.coordinates),
            radius=radius,
            color=color,
            fill=False,
            linestyle=linestyle,
            label=label,
        )


# Create a transformer from WGS84 3D Ellipsoidal to WGS84 + EGM96 Sea Level Altitude
# EPSG:4979 is Latitude/Longitude/Ellipsoidal height (3D)
# EPSG:5773 is EGM96 orthometric height (altitude above sea level)
altitude_transformer = Transformer.from_crs(
    "EPSG:4979", "EPSG:4326+5773", always_xy=True
)


def to_altitude(lat, lon, ellipsoidal_height):
    """Convert ellipsoidal height to altitude above sea level."""
    lon, lat, altitude = altitude_transformer.transform(lon, lat, ellipsoidal_height)
    return altitude


def to_utm(lon, lat):
    """Convert latitude and longitude to UTM coordinates."""
    return transformer.transform(lon, lat)


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate distance between two geographic coordinates using the Haversine formula.
    Doesn't need to be transformed to UTM first.
    """
    R = 6371000.0  # Earth radius in meters

    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Distance in meters


def distance_mask(
    center: tuple[float, float],
    lon: NDArray,
    lat: NDArray,
    distance: float,
):
    """
    Create a boolean mask for points within a certain distance from a center point.
    """

    def compute_distance(gps):
        return haversine(*center, *gps)
    return array(list(map(compute_distance, zip(lon, lat)))) < distance


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


type AllowedGeometry = LineString | Polygon | MultiPolygon | MultiLineString
type GeoFeatureCollection = FeatureCollection[Feature[AllowedGeometry, BaseModel]]


def load_geojson(file_path: Path) -> GeoFeatureCollection:
    """
    Load a GeoJSON file and return it as a GeoFeatureCollection.
    """
    with open(file_path, "r", encoding="utf-8") as fid:
        return FeatureCollection.model_validate_json(fid.read())


class Scale(Enum):
    M = 1.0
    KM = 0.001

def plot_geojson_feature(
    ax: Axes,
    feature: Feature[AllowedGeometry, BaseModel],
    lower_left: Optional[tuple[float, float]],
    upper_right: Optional[tuple[float, float]],
    color: str,
    linewidth: float,
    scale: Scale,
):
    """
    Plot the features of a GeoFeatureCollection on the given Matplotlib Axes. Tested
    with LineString, MultiLineString, MultiPolygon and Polygon geometries.
    """
    geometry = feature.geometry
    if geometry is None:
        raise ValueError("Feature geometry is None")
    if "Multi" in geometry.type or geometry.type == "Polygon":
        parts = geometry.coordinates
    else:  # really just LineString
        parts = [geometry.coordinates]
    for part in parts:
        coords = array(part).reshape(-1, 2)
        if lower_left is not None:
            if (coords.max(axis=0) < array(lower_left)).any():
                continue
        if upper_right is not None:
            if (coords.min(axis=0) > array(upper_right)).any():
                continue
        x, y = to_utm(*coords.T)
        ax.plot(
            scale.value * x,
            scale.value * y,
            color=color,
            linewidth=linewidth
        )


def plot_map(
    ax: Axes,
    lower_left: Optional[tuple[float, float]],
    upper_right: Optional[tuple[float, float]],
    linewidth: float,
    scale: Scale,
    color: str,
):
    """
    Plot a map with the given lower-left and upper-right coordinates.
    """
    for feature_file in ["maine", "tide-line"]:
        filepath = (TMP_DIR / feature_file).with_suffix(".geojson")
        if not filepath.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {filepath}")
        for feature in load_geojson(filepath).features:
            plot_geojson_feature(
                ax,
                feature,
                lower_left=lower_left,
                upper_right=upper_right,
                color=color,
                linewidth=linewidth,
                scale=scale
            )
    if lower_left is not None:
        x, y = to_utm(*lower_left)
        ax.set_xlim(left = scale.value * x)
        ax.set_ylim(bottom = scale.value * y)
    if upper_right is not None:
        x, y = to_utm(*upper_right)
        ax.set_xlim(right = scale.value * x)
        ax.set_ylim(top = scale.value * y)

    # display UTM coordinates w/o exponential notation
    ax.ticklabel_format(axis="both", style="plain")
    ax.set_xlabel(f"UTM Easting ({scale.name.lower()})")
    ax.set_ylabel(f"UTM Northing ({scale.name.lower()})")
    ax.set_aspect("equal", adjustable="box")
