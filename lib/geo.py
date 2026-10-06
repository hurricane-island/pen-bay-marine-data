"""
Geospatial and mapping utilities for plotting geographic data on a map.
"""
from enum import StrEnum, auto
import json
from typing import Optional, cast
from pathlib import Path
from click import group, argument, option, Choice, echo
from pandas import read_csv, DataFrame, cut
from numpy import arange, array, column_stack, meshgrid, linspace, interp, nan
from matplotlib.pyplot import subplots, close, Axes
from pydantic import BaseModel
from scipy.interpolate import griddata
from pyproj import Transformer
from gsw import rho
from lib import haversine
from geojson_pydantic import FeatureCollection, Feature, LineString, MultiLineString, Polygon, MultiPolygon


TMP_DIR = Path(__file__).parent.parent / "tmp"
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)

def plot_map(ax: Axes):


    with open(TMP_DIR / "maine.geojson", "r", encoding="utf-8") as f:
        geojson_data_maine: FeatureCollection[Feature[LineString|Polygon|MultiPolygon, BaseModel]] = FeatureCollection.model_validate_json(f.read())

    for feature in geojson_data_maine.features:
        geometry = feature.geometry
        if geometry is None:
            continue
        count = len(geometry.coordinates)
        if count == 1:
            x, y = transformer.transform(*array(geometry.coordinates).T)
            ax.plot(x, y, color="grey", linewidth=0.5)
        else:
            for poly in geometry.coordinates:
                x, y = transformer.transform(*(array(poly).T))
                ax.plot(x, y, color="grey", linewidth=0.5)


    with open(TMP_DIR / "tide-line.geojson", "r", encoding="utf-8") as f:
        geojson_data_tides: FeatureCollection[Feature[LineString | MultiLineString, BaseModel]] = FeatureCollection.model_validate_json(f.read())

    for feature in geojson_data_tides.features:
        geometry = feature.geometry
        if geometry is None:
            continue
        geom_type = geometry.type
        coordinates = geometry.coordinates
        if geom_type == "LineString":
            x, y = transformer.transform(*zip(*coordinates))
            ax.plot(x, y, color="green", linewidth=0.5)
        elif geom_type == "MultiLineString":
            for line in coordinates:
                x, y = transformer.transform(*zip(*line))
                ax.plot(x, y, color="green", linewidth=0.5)
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")

    ax.set_title("Map")
    ax.set_xlabel("UTM Easting (m)")
    ax.set_ylabel("UTM Northing (m)")
    ax.set_aspect('equal', adjustable='box')