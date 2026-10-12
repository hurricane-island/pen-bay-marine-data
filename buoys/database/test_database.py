"""
Tests for the buoy database commands.
"""

from click.testing import CliRunner
from pytest import mark
from buoys.options import StationName, TableName
from buoys.database import (
    buoys_db_create,
    buoys_db_delete,
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


@mark.parametrize("name", StationName)
@mark.parametrize("table", TableName)
def test_cli_buoys_db_upload(name: StationName, table: TableName):
    """
    Test the CLI command for uploading buoy data to the database.
    """
    result = runner.invoke(buoys_db_upload, args=[name, table, DATABASE_NAME])
    assert (
        result.exit_code == 0
    ), f"Upload failed for table {table} with output: {result.output}"


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
