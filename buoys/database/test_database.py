"""
Tests for the buoy database commands.
"""

from click.testing import CliRunner
from pytest import mark
from buoys.options import StationName, TableName, DATA_DIR
from pathlib import Path
from buoys.database import (
    buoys_db_create,
    buoys_db_delete,
    buoys_db_diff,
    buoys_db_upload,
    buoys_db_describe,
)

runner = CliRunner()

DATABASE_NAME = "buoys-test"


def test_cli_buoys_db_create():
    """
    Test the CLI command for creating the buoy database.
    """
    result = runner.invoke(buoys_db_create, args=[DATABASE_NAME])
    assert result.exit_code == 0, f"Create failed with output: {result.output}"


@mark.parametrize("filename", DATA_DIR.glob("*.dat"))
def test_cli_buoys_db_upload_file(filename: Path):
    """
    Test the CLI command for uploading buoy data to the database.
    """
    result = runner.invoke(buoys_db_upload, args=[str(filename), DATABASE_NAME])
    assert (
        result.exit_code == 0
    ), f"Upload failed for file {filename} with output: {result.output}"

@mark.parametrize("filename", DATA_DIR.glob("*.dat"))
def test_cli_buoys_db_diff_file(filename: Path):
    """
    Test the CLI command for diffing buoy data against the database.
    """
    result = runner.invoke(buoys_db_diff, args=[str(filename), DATABASE_NAME])
    assert (
        result.exit_code == 0
    ), f"Diff failed for file {filename} with output: {result.output}"

@mark.parametrize("name", StationName)
@mark.parametrize("table", TableName)
def test_cli_buoys_db_describe(name: StationName, table: TableName):
    """
    Test the CLI command for describing the buoy database.
    """
    result = runner.invoke(buoys_db_describe, args=[name, table, DATABASE_NAME])
    assert result.exit_code == 0


def test_cli_buoys_db_delete():
    """
    Test the CLI command for deleting the buoy database.
    """
    result = runner.invoke(buoys_db_delete, args=[DATABASE_NAME], input="y\n")
    assert result.exit_code == 0
