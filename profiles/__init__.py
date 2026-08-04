import click

@click.group()
def profiles():
    """Profile CLI commands."""
    pass


@profiles.group()
def plot():
    """Plot CLI commands."""
    pass

@plot.command(name="single")
def profiles_plot():
    """Plot a single depth profile, e.g., temperature, salinity, or density."""
    pass
