"""
Quality assurance and quality control (QA/QC) for buoy data using QARTOD tests.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from click import option, Choice
from yaml import safe_load
from numpy import where
from pandas import concat, DataFrame
from ioos_qc.config import Config
from ioos_qc.streams import PandasStream
from ioos_qc.stores import PandasStore


class TestTypes(Enum):
    """
    Supported QARTOD test types.
    """

    GROSS_RANGE = "gross_range"
    RATE_OF_CHANGE = "rate_of_change"
    SPIKE = "spike"
    CLIMATOLOGY = "climatology"
    FLAT_LINE = "flat_line"
    ROLLUP = "rollup"
    GAP = "gap"
    LOCATION = "location"


qartod_configs_option = option(
    "--qartod",
    "-q",
    multiple=True,
    type=str,
    help=(
        "QARTOD configuration file(s). Accepts multiple YAML files, "
        "which will be merged together in the order they are provided."
    ),
)


qartod_test_option = option(
    "--test",
    default=TestTypes.ROLLUP,
    type=Choice(TestTypes, case_sensitive=False),
    help="QARTOD test to plot.",
)


def deep_merge_inplace(base: dict, update: dict) -> None:
    """
    Recursively merges update into base in-place.

    Nested dictionaries are merged. All other types (including lists, sets,
    and primitives) are overwritten by the value in update.
    """
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge_inplace(base[key], value)
        else:
            base[key] = value


def load_and_merge_qa_configs(qartod: tuple[str]) -> dict:
    """
    Load the default QARTOD configuration and merge it with any user-provided
    configuration files. The user-provided configurations will override the defaults.
    """
    accumulate = {}
    for file in qartod:
        qa_path = Path(__file__).parent / file
        if not qa_path.exists():
            raise FileNotFoundError(f"QARTOD configuration file not found: {qa_path}")
        with open(qa_path, "r", encoding="utf-8") as fid:
            deep_merge_inplace(accumulate, safe_load(fid))
    return accumulate


def get_climatology_breakpoints(config_key_value: dict, series: str) -> list:
    """
    Extract climatology breakpoints from the QARTOD configuration for a specific series.
    """
    climatology_breakpoints = (
        config_key_value["streams"][series]["qartod"]
        .get("climatology_test", {})
        .get("config", [])
    )
    breaks = []
    for each in climatology_breakpoints:
        for yr in (2025, 2026):
            breaks.append(datetime(month=each["tspan"][0], day=1, year=yr))
    return breaks


def test_observed_property(
    result: DataFrame, observed_property: str, tests: list[str], group_by_key: str
) -> DataFrame:
    """
    Get quality assurance flags for observed property. We temporarily
    replace missing values with -1 to avoid them affecting the rollup calculation,
    and then revert them back to 9 after processing.
    """
    columns = {
        f"{observed_property}_qartod_{test}": test.replace("_test", "")
        for test in tests
    }
    df = result[columns.keys()].rename(columns=columns).replace(9, -1)
    df[TestTypes.ROLLUP.value] = df.max(axis=1).astype("object")
    for col in df.columns:
        df[col] = df[col].astype("object")
    df[group_by_key] = observed_property
    return df.replace(-1, 9)


def tests_per_observed_property(result: DataFrame) -> dict[str, list[str]]:
    """
    Extract observed properties and their associated tests.
    """
    frames: dict[str, list[str]] = {}
    for each in result.columns:
        _series, _name = each.split("_qartod_")
        if _series not in frames:
            frames[_series] = []
        frames[_series].append(_name)
    return frames


def run_qartod_tests(
    df,
    config: dict,
    time_col: str = "time",
    lat_col: str = "Latitude",
    lon_col: str = "Longitude",
):
    """
    Run QARTOD tests on the provided data using the specified configuration. This
    expects latitude and longitude columns to be present in the DataFrame for
    location-based tests.
    """
    flags = PandasStream(
        df=df.reset_index(names=time_col),
        time=time_col,
        lat=lat_col,
        lon=lon_col,
    ).run(Config(config))
    result = (
        PandasStore(flags).save().set_index(time_col).drop(columns=["lat", "lon"])
    )
    frames = tests_per_observed_property(result)
    by_observed_property = []
    group_by_key = "observed_property"
    for key, tests in frames.items():
        flags = test_observed_property(result, key, tests, group_by_key)
        flags[TestTypes.GAP.value] = where(df[key].isna(), 3, 1)
        by_observed_property.append(flags)
    return concat(by_observed_property, axis=0).groupby(group_by_key)
