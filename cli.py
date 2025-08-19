"""
Entry point for Command Line Interface (CLI)
"""
from pandas import set_option
from click import group
from weather import weather
from buoys import buoys

@group()
def cli():
    """
    Command Line Interface for weather and buoy data.
    """

cli.add_command(weather)
cli.add_command(buoys)

if __name__ == "__main__":
    set_option("display.max_columns", None)
    set_option("display.max_rows", None)
    cli()
