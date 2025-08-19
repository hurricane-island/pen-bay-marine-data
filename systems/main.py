"""
Read data from either the exported CSV files from Govee or Sol Ark devices, 
or query the API for each. Visualize the data.
"""
from os import listdir, path
from sys import argv
from pandas import DataFrame, read_csv, to_datetime, concat
from matplotlib.pyplot import subplots, title
from matplotlib.axes import Axes

class TimeSeries:
    """
    A simple class to hold information about a time series
    for plotting purposes.
    """
    def __init__(
        self,
        source: DataFrame,
        column: str,
        alias: str,
        color: str,
        resample_rule: str = 'D'  # Default to daily resampling
    ) -> None:
        # Source column name
        self.column = column
        # New name to assign to the column in the plot
        self.alias = alias
        # Color for the plot and axis label
        self.color = color
        # Source data
        self.resampler = source[column].resample(resample_rule)

    def plot_resampled_range(
        self,
        # Matplotlib axis context
        axis: Axes,
    ) -> None:
        """
        Resample and plot time series data as high/low envelope. Limits
        for axes are set from the range of timestamp and data.
        """
        resample_high = self.resampler.max()
        resample_low = self.resampler.min()
        axis.plot(
            resample_high.index, 
            resample_high,
            color=self.color
        )
        axis.plot(
            resample_low.index, 
            resample_low,
            color=self.color
        )
        axis.set_xlim(resample_high.index[0], resample_high.index[-1])
        axis.set_ylabel(self.alias, color=self.color)
        axis.set_ylim(resample_low.min(), resample_high.max())

def timestamped_csv_to_df(
    # Full file path
    file_path: str,
    # Set time column as index
    time_column: str
) -> DataFrame:
    """
    Read CSV file and convert it to a DataFrame,
    with a datetime index. The result can be
    concatenated with other DataFrames.
    """
    df = read_csv(file_path)
    current_columns = df.columns.to_list()
    new_columns = {
        column: column.replace("\xa0", " ") 
        for column in current_columns
    }
    df.rename(columns=new_columns, inplace=True)
    df[time_column] = to_datetime(df[time_column])
    return df.set_index(time_column)

def concatenate_time_indexed_data(
    # Search directory for partial data files
    directory: str,
    # Prefix to match for the files to include
    prefix: str,
    # File format to match
    file_format: str,
    # Column to use as the time index
    time_column: str
) -> DataFrame:
    """
    Collate data from all CSV files in a single DataFrame,
    and sorted chronologically by the index.
    """
    dfs = []
    for file in listdir(directory):
        if file.startswith(prefix) and file.endswith(file_format):
            file_path = path.join(directory, file)
            df = timestamped_csv_to_df(file_path, time_column)
            dfs.append(df)
    return concat(dfs).sort_index()

def plot_on_two_y_axes(
    # Size of the figure
    figure_size: tuple,
    # File path to save the figure
    file_name: str,
    # Title for the figure
    figure_title: str,
    # Label for the x-axis
    time_label: str,
    # Two time series to plot on twinned y-axes
    series: tuple[TimeSeries, TimeSeries]
) -> None:
    """
    Plot temperature and humidity data from DataFrame on two y-axes.
    """
    figure, axis = subplots(figsize=figure_size)
    left, right = series
    axis.set_xlabel(time_label)
    left.plot_resampled_range(axis)
    right.plot_resampled_range(axis.twinx())
    title(figure_title)
    figure.tight_layout()
    figure.savefig(file_name)

def load_and_plot_govee_data(
    # Directory containing the Govee CSV files
    directory: str,
    figures_size: tuple,
    out_path: str,
    resample_rule: str
) -> None:
    thermometer = concatenate_time_indexed_data(
        directory=directory,
        prefix=f"Smart Thermometer {1}_export_",
        file_format=".csv",
        time_column="Timestamp for sample frequency every 60 min min"
    )
    print(thermometer.dtypes)
    print(thermometer.head())
    temperature_series = TimeSeries(
        source=thermometer,
        column="Temperature_Fahrenheit",
        alias="temperature (°F)",
        color="red",
        resample_rule=resample_rule
    )
    humidity_series = TimeSeries(
        source=thermometer,
        column="Relative_Humidity",
        alias="humidity (%)",
        color="black",
        resample_rule=resample_rule
    )
    plot_on_two_y_axes(
        figure_size=figures_size,
        file_name=out_path,
        figure_title='Daily temperature and humidity range at Field Research Station',
        time_label='date',
        series=(temperature_series, humidity_series)
    )

def sol_ark_csv_to_df(directory: str) -> DataFrame:
    """
    Read Sol Ark CSV file and convert it to a DataFrame.
    """
    file_path = path.join(
        directory, '2308242296-2025-07-29.xlsx - sheet1.csv')
    sol_ark_time = "Time"
    df = read_csv(file_path, skiprows=5)
    df[sol_ark_time] = to_datetime(df[sol_ark_time])
    df = df.set_index(sol_ark_time)
    return df

def plot_sol_ark_power(
    data_frame: DataFrame,
    column: str,
    rename: str,
    color: str,
    axis: Axes
) -> None:
    """
    Plot a single series.
    """
    values = data_frame[column]
    axis.plot(
        data_frame.index, 
        values,
        color=color,
        label=rename
    )
    axis.set_xlabel('date and time')
    axis.set_xlim(data_frame.index[0], data_frame.index[-1])
    axis.set_ylim(values.min(), values.max())
    axis.set_ylabel(rename, color=color)

def plot_sol_ark_data(df: DataFrame, out_dir: str = "figures") -> None:
    """Plot Sol Ark data from DataFrame."""
    fig, ax = subplots(figsize=(10, 3))
    plot_sol_ark_power(df, "LoadTotalPower(W)/178", "load (W)", "red", ax)
    ax2 = ax.twinx()
    plot_sol_ark_power(df, "BatteryEnergy(A·H)/184", "state of charge (%)", "black", ax2)
    title('Power and state of charge at Field Research Station')
    # fig.legend()
    fig.tight_layout()
    fig.savefig(f"{out_dir}/power-and-state-of-charge.png")

if __name__ == "__main__":
    # produce the plots
    OUT_DIR = "figures"
    LOCAL_PATH = argv[1]
    FIGURE_SIZE = (10, 3)
    load_and_plot_govee_data(
        directory=LOCAL_PATH,
        figures_size=FIGURE_SIZE,
        out_path=f"{OUT_DIR}/temperature-and-humidity.png",
        resample_rule="D"
    )
    # power = sol_ark_csv_to_df(LOCAL_PATH)
    # columns = power.columns
    # for col in columns:
    #     print(f"{col}: {power[col].dtype}")
    # print(power.head())
    # plot_sol_ark_data(power)
