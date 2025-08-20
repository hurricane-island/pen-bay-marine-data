# pylint: disable=unreachable
"""
This is an introduction to working with data in Python.

In Python, the main data types are:
    int, float, str, bool, list, tuple, set, dict

Built in functions:
- `len()` will tell you the length of the list
- `print()` print in output
- `type()` will tell you the data type
- `sys.exit()` will stop the program

Example of Quality Assurance of Real-Time Oceanographic Data (QARTOD),
using IOOS open source library.

Quality flags:
1 = pass
2 = test not run on this data
3 = suspect
4 = fail
9 = missing data
"""

# These are imports, they always go at the top of the file.
# For example, `datetime` is a  module that allows us to
# use functions and constants related to time keeping
import sys # for debugging, to stop the program
from datetime import datetime
from typing import Any  # for type hinting
from ioos_qc.qartod import (
    gross_range_test,
    spike_test,
    ClimatologyConfig,
    climatology_test,
)  # quality control
from ioos_qc.config import Config
from ioos_qc.streams import PandasStream
from ioos_qc.stores import PandasStore
from pandas import DataFrame, read_csv, to_datetime  # data frames
from numpy.typing import NDArray  # for type hinting
# local functions and constants from `examples.py`
from examples import (
    iso_time_format,
    DATA_DIR,
    plot_qc_results,
)

column_1 = "Time"  # This is defining the variable column_1 and assigning a string
column_2 = "Temperature"  # Strings are sequences of characters
column_3 = "Conductivity"  # Strings can be defined with single quotes
column_4 = "Salinity"  # strings can also be defined with double quotes
column_5 = "Chlorophyll"
column_6 = "BGA_PE"  # PE stands for phycoerythrin

# To store all these variables, we can use a list, tuple, or dictionary.

# A list is an ordered collection of items that can be changed
buoy_parameters_list = [column_1, column_2, column_3, column_4, column_5, column_6]

# A tuple is an ordered collection like a list, but cannot be changed
buoy_parameters_tuple = (column_1, column_2, column_3, column_4, column_5, column_6)

# You can remove items from a list using the remove() method
buoy_parameters_list.remove(column_1)

# You can print using the print() function
print("list -", "The parameters we are measuring are: ", buoy_parameters_list)

# You can add items to a list using the append() or insert() method
# append() adds to the end of the list
buoy_parameters_list.append(column_1)

# Lists are indexed starting with 0.
# By specifying 0 in the line below, column_1 will be added in the first position of the list.
buoy_parameters_list.insert(0, column_1)

# You can also add multiple items to a list using the extend() method
buoy_parameters_list.extend(["New Column A", "New Column B"])

# A dictionary is an unordered collection of key-value pairs
buoy_parameters_dict = {
    "TIMESTAMP": column_1,
    "External_Temp": column_2,
    "Conductivity_us": column_3,
    "Salinity": column_4,
    "Chlorophyll_RFU": column_5,
    "BGA_PE_RFU": column_6,
}

# The keys are the names of the parameters in the raw data,
# and the values are the variables we defined earlier
# with our naming convention.
# You access the values in a dictionary using the keys
# To print only the values, add .values() to the end of the dictionary
# To print only the keys, add .keys() to the end of the dictionary
print("dict -", f"The parameters we are measuring are: {buoy_parameters_dict}")

# Lists, tuples, and dictionaries are all examples of
# data structures in Python. They can hold strings
# (like we have used above) and other data types like integers,
# floats, and booleans. An integer is a whole number, a float
# is a number with a decimal point, and a boolean is either
# True or False.

# We will try to do a quality control check on some example data.
# This is a list of example chlorophyll data in
# relative fluorescence units (RFU)
chlorophyll_ex_data = [
    10.3,
    68.1,
    4.4,
    71.9,
    45.2,
    12.5,
    0.0,
    100.0,
    50.0,
    5.0,
]

# Python has useful built-in functions in the standard library
# Imagine we got all the same values...
# len() and print() are built in python functions.
# len() tells you the length of the list
print("functions -", len(chlorophyll_ex_data))

# Defining the sensor limits
SENSOR_MAX = 100  # units: RFU, this is an integer
SENSOR_MIN = 0.0  # RFU, this is a float because it has a decimal point
USER_MAX = 50  # RFU, integer
USER_MIN = 5.0  # RFU, float

# Booleans are a data type that can only be True or False.
# They are often used to control the flow of the program.
# For example, we can use a boolean to check if the data
# is valid or not.

# We are going to use a for loop to iterate through the chlorophyll
# data and check if the values are within the sensor and user limits.
# We will use if-else statements to check the values and print
# a message if they are outside the sensor and user limits.
for value in chlorophyll_ex_data:
    if value > SENSOR_MAX or value < SENSOR_MIN:
        # value is outside the sensor limits
        print(f"bool - {value} is outside of sensor limits")
    elif value > USER_MAX or value < USER_MIN:
        # value is outside the user limits
        print(f"bool - {value} is outside of user limits")
    else:
        pass


# Lets say if one value is outside the sensor limits,
# the data is not valid and we want to stop the loop.
# This is a for loop that will iterate through each value
# in the chlorophyll_ex_data list
for value in chlorophyll_ex_data:
    if value > SENSOR_MAX or value < SENSOR_MIN:
        # stop the loop if the value is outside the sensor limits
        break
    # Because we break, we don't need an `elif` statement here
    if value > USER_MAX or value < USER_MIN:
        # value is outside the user limits
        print(f"bool - {value} is outside of user limits")
    else:
        pass


# You can also write functions that perform defined tasks.
# The inputs to the function are called an arguments, and the
# variables within the function are called parameters.
# To write your own function, you first need to define it.
# For example, the raw data provides dates and time
# like this, 4/24/25 17:00, but we want the time to
# be formatted like 2025-04-24T17:00:00Z, which is called
# ISO 8601 formatting
def my_function() -> datetime:
    """
    Functions should have a docstring (like this) that describes
    what it does. This function shows the current time, and
    whatever message you passed in as an argument.
    """
    return datetime.now()


print("functions -", my_function())  # for a function to run, it must be called

# Some example timestamps to parse into dates
timestamp = [
    "2025-04-24 17:00:00",
    "2025-04-24 18:00:00",
    "2025-04-24 19:00:00",
    "2025-04-24 20:00:00",
    "2025-04-24 21:00:00",
    "2025-04-24 22:00:00",
    "2025-04-24 23:00:00",
    "2025-04-25 0:00:00",
    "2025-04-25 1:00:00",
]

# for a function to run, it must be called
# we want to iterate through each item in the list timestamp
# you can also use the index of the item in your loop
for ind, item in enumerate(timestamp):
    print(f"functions - list item {ind}: {iso_time_format(item)}")

# Other builtin functions can be used for program flow.
# If you want to run just part of this file, you use the `exit()`
# function at the point you want to stop. For example, comment the
# next line and run with `pixi run python tutorial.py`...
# sys.exit()

# So far we have worked with simple example data, now we will work
# with a real data set from one of the buoys.
filepath = DATA_DIR / "buoy.csv"

# Read select columns where the column headers are in the second row
# Doesn't have coordinates for location test, but fixed platforms are exempt
df: DataFrame = read_csv(
    filepath,
    usecols=[
        "TIMESTAMP_ISO",
        "External_Temp",
        "Conductivity_us",
        "SpConductivity_us",
        "Salinity",
        "Chlorophyll_ugL",
        "Chlorophyll_RFU",
        "BGA_PE_RFU",
        "BGA_PE_ugL",
    ],
)
df["TIMESTAMP_ISO"] = to_datetime(df["TIMESTAMP_ISO"])
print("pandas - ", df.head())  # Print the first five rows of the dataframe

# Count the number of blanks in the df
blank_count = df.isna().sum().sum()
print(f"pandas - blank count: {blank_count}")

# Count the number of duplicates in the df
duplicate_count = df.duplicated().sum()
print(f"pandas - duplicate count: {duplicate_count}")

# Check if the data falls within the expected range
fail_span = [SENSOR_MIN, SENSOR_MAX]
suspect_span = [USER_MIN, USER_MAX]
series = df["Chlorophyll_RFU"]
results_gr = gross_range_test(
    inp=series, fail_span=fail_span, suspect_span=suspect_span
)
# How many results are suspect or fail
suspect_fail_range = (results_gr > 2).sum()
print("tests - range: suspect or fail", suspect_fail_range)

# Check if the data decreases or increases more rapidly than is realistic
results_spike = spike_test(
    inp=series, suspect_threshold=0.25, fail_threshold=0.5, method="average"
)

# How many results are suspect or fail
suspect_fail_spike: NDArray[Any] = (results_spike > 2).sum()
print("tests - spike:suspect or fail", suspect_fail_spike)

# How many results failed
failed: NDArray[Any] = (results_spike == 4).sum()
print("tests - spike:fail", failed)

# In stream below, replace with names of the time, depth, latitude, and longitude column
stream = PandasStream(
    df, z="Depth", lat="Lat", lon="Long", geom=None, time="TIMESTAMP_ISO"
)

# Define configuration for gross range tests

config = f"""
streams:
    External_Temp:
        qartod:
            gross_range_test:
                suspect_span: [0.56, 22]
                fail_span: [-5, 50]
    Conductivity_us:
        qartod:
            gross_range_test:
                suspect_span: [15000, 35000]
                fail_span: [0, 100000]
    Chlorophyll_RFU:
        qartod:
            gross_range_test:
                suspect_span: [{USER_MIN}, {USER_MAX}]
                fail_span: [{SENSOR_MIN}, {SENSOR_MAX}]
    BGA_PE_RFU:
        qartod:
            gross_range_test:
                suspect_span: [{USER_MIN}, {USER_MAX}]
                fail_span: [{SENSOR_MIN}, {SENSOR_MAX}]
"""

# Run tests
flags = stream.run(Config(config))


# Append the QC flags onto the dataframe
store = PandasStore(flags, axes=None)
with_flags = store.save(write_data=True, write_axes=True, include=None, exclude=None)

# Plot the results
plot_qc_results(with_flags, 'External_Temp', 'External_Temp_qartod_gross_range_test', 'Temperature QC')


# Run climatology test
new_config = ClimatologyConfig(members=None)
params = {
    "tspan": [
        df.index[0],
        df.index[-1],
    ],  # time span
    "vspan": [0.56, 13.3],  # outside will be suspect
    "fspan": [0.56, 22],  # outside will fail
    "zspan": None,  # depth span
    "period": None,  # the period, if included need to change tspan
}
new_config.add(**params)

climatology_result = climatology_test(
    config=new_config,
    inp=df["External_Temp"],
    tinp=df["TIMESTAMP_ISO"],
    zinp=None,
)

# adds the climatology test flags to the dataframe
df["external_temp_climatology_test"] = (
    climatology_result
)

# Plot climatology test results
# plot_qc_results(data, 'TIMESTAMP_ISO', 'External_Temp', 'external_temp_climatology_test', 'Climatology Test for Temp')

# Not required, but prevents warnings if commented out elsewhere
sys.exit()