"""
Example of processing a CSV file with pandas. Once you understand how things
work, use these methods to analyze your own data.

Not covered:
- check a daily trend
- add another series
- subplots
"""

from datetime import datetime
from pathlib import Path
from pandas import DataFrame, read_csv, to_datetime
from matplotlib import pyplot as plt
from matplotlib.dates import WeekdayLocator, DateFormatter

FIGURES = Path(__file__).parent / "figures"
DATA_DIR = Path(__file__).parents[1] / "buoys" / "data"
EXAMPLE = Path(__file__).parent / "data" / "buoy.csv"


def iso_time_format(time: str) -> str:
    """
    This will print the current time in iso format
    (this is a built in python function)
    """
    timestamp = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    return timestamp.isoformat()


def time_format(ts: list[str]) -> list:
    """
    Convert the current time to ISO 8601 formatting
    """
    timestamp_dt = [
        datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S") for timestamp_str in ts
    ]
    timestamp_iso = [
        datetime.isoformat(timestamp_str) for timestamp_str in timestamp_dt
    ]
    return timestamp_iso


def select_columns(filename: str, columns: list[str]) -> DataFrame:
    """
    Read a CSV file and select specific columns.
    """
    # for our purposes, I only want to read select columns where the
    # column headers are in the second row
    df: DataFrame = read_csv(filename, header=1, usecols=columns)

    # drop the first row below the headers which contain units
    df.drop(0, axis=0, inplace=True)

    # and the second row for analysis purposes
    df.drop(1, axis=0, inplace=True)

    # resets the index
    df = df.reset_index(drop=True)

    timestamp = df["TIMESTAMP"].tolist()
    timestamp_clean = time_format(timestamp)

    # drops the old time column in the wrong format
    df = df.drop("TIMESTAMP", axis="columns")

    # inserts new time column leftmost
    df.insert(loc=0, column="TIMESTAMP_ISO", value=timestamp_clean)

    return df


def show_blank_and_duplicate_counts(df: DataFrame) -> None:
    """
    Print the number of blanks and duplicates in the DataFrame.
    """
    blank_count = df.isna().sum()
    print(f"Blank count: {blank_count}")

    duplicate_count = df.duplicated().sum()  # count the number of duplicates in the df
    print(f"Duplicate count: {duplicate_count}")


def from_csv(filename: str, describe: bool = False) -> DataFrame:
    """
    Parse data frame from a CSV
    """
    file_path = DATA_DIR / filename
    time_col = "TIMESTAMP_ISO"
    df: DataFrame = read_csv(file_path, header=0)
    if describe:
        print(df.head())
        print(
            df.describe()
        )  # The describe function provides summary statistics on each column
    time = df[time_col].to_list()  # This will be our x-axis
    df[time_col] = to_datetime(time)
    # OR: [datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S") for timestamp_str in time]
    return df.set_index(time_col)


def heatmap(filename: str) -> None:
    """
    Heatmap visualization, demonstrating rasterization of
    time series data
    """
    df = from_csv(filename)
    day = [timestamp_str.day for timestamp_str in df.index]
    hour = [timestamp_str.hour for timestamp_str in df.index]
    values = df["Chlorophyll_RFU"].to_list()
    subset = DataFrame({"day": day, "hour": hour, "Chlorophyll": values})
    print(subset.describe())
    plt.figure(figsize=(4, 3))
    plt.imshow(subset, cmap="viridis", vmin=0, vmax=1)
    plt.colorbar()
    plt.savefig("figures/heatmap.png")


def plot(filename: str) -> None:
    """
    Get a Series from a DataFrame and plot it as a line graph.
    """
    df: DataFrame = from_csv(filename)

    chlorophyll = df["Chlorophyll_RFU"]  # This will be our y-axis
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Chlorophyll (RFU)")
    ax.set_title("Time series example")
    # ax.set_xticklabels(rotation=45)
    ax.set_ylim(0, 1.5)
    # I only wanted to look at this time period
    ax.set_xlim(datetime(2025, 5, 1, 9, 0), datetime(2025, 5, 10, 10, 0))
    # helpful feature of matplotlib that autofits dates into the x-axis
    plt.gcf().autofmt_xdate()
    # This provides the red shading to emphasize one period within the figure
    plt.axvspan(
        datetime(2025, 5, 1, 12, 0), datetime(2025, 5, 3, 12, 0), color="red", alpha=0.3
    )
    ax.plot(
        chlorophyll.index,
        chlorophyll,
        color="r",
        linewidth=1.0,
        linestyle="-",
        label="chlorophyll",
    )
    ax.legend(loc="upper right")  # The legend will look for "label" in the plot line
    fig.tight_layout()
    fig.savefig("figures/series.png")  # example of saving the plot as a png

def color_code(flag: int) -> str:
    if flag == 4:
        return "red"
    elif flag == 3:
        return "orange"
    elif flag == 2:
        return "gray"
    elif flag == 1:
        return "green"
    else:
        return "blue"


def plot_qc_results(df: DataFrame, var_col: str, qc_test_col: str, title: str):
    """
    df = Dataframe containing the data
    var_col = Name of column containing the variable data
    qc_test_col = Name of the column containing the QC test results
    title = Title of the plot
    """
    times = df["time"]
    fig, ax = plt.subplots(figsize=(4, 3))
    mask = df[qc_test_col] != 1
    count = mask.sum()
    if count > 0:
        flagged = df[mask]
        flagged_colors = flagged.map(color_code)
        ax.scatter(flagged["time"], flagged[var_col], marker="o", color=flagged_colors)
    ax.plot(times, df[var_col], color="black", linestyle="-")
    ax.set_xlabel("Date")
    ax.set_ylabel(var_col)
    ax.set_title(f"{title} - {count} of {len(df)} flagged")
    plt.gcf().autofmt_xdate()
    ax.xaxis.set_major_locator(WeekdayLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    fig.tight_layout()
    fig.savefig(FIGURES / "qartod.png")


def flat_line_test(series: list[float]) -> None:
    """
    Perform the flat line test on a time series,
    using our own implementation.
    """
    for x in series:
        if not isinstance(x, int) is True:
            break
        series = iter(series)
        if x != next(series):
            response = "Flat line test passed"
        elif x != next(series):
            response = "Flat line test passed"
        else:
            response = "Flat line detected"
            break
    return print(response)


if __name__ == "__main__":
    # Run this file directly to execute the example
    SOURCE = DATA_DIR / "Wynken_SondeValues_2025-05-14T22-45.dat"
    COLUMNS = [
        "TIMESTAMP",
        "External_Temp",
        "Conductivity_us",
        "SpConductivity_us",
        "Salinity",
        "Chlorophyll_ugL",
        "Chlorophyll_RFU",
        "BGA_PE_RFU",
        "BGA_PE_ugL",
    ]
    data = select_columns(SOURCE, COLUMNS)
    print(data.head())  # print the first five rows
    show_blank_and_duplicate_counts(data)
    data.to_csv(EXAMPLE, index=False)
    if not FIGURES.exists():
        FIGURES.mkdir()
    heatmap(EXAMPLE)
    plot(EXAMPLE)