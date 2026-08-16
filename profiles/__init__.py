"""
Command line interfaces for working with vertical profiles of water column data, such as temperature, salinity, and density.
"""
import click

@click.group()
def profiles():
    """Profile CLI commands."""


@profiles.group()
def plot():
    """Plot CLI commands."""


@plot.command(name="single")
def profiles_plot():
    """Plot a single depth profile, e.g., temperature, salinity, or density."""
    click.echo("Not yet implemented")
