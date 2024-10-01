import streamlit as st
import pandas as pd
import seaborn as sns, os
import matplotlib.pyplot as plt
from fredapi import Fred
from bls import get_series

# load APIs
# from dotenv import load_dotenv
# load_dotenv()

# Configure FRED and BLS API keys
API_KEY = os.getenv('FRED_API_KEY')
# os.environ['BLS_API_KEY'] = os.getenv('BLS_API_KEY')

# Initialize FRED API
fred = Fred(api_key=API_KEY)

def plot_series_with_vlines(series_dict, title, legend_text_generator, from_date='2000-01-01', x_label='Date', y_label='Series Value', change_in=False, legend_loc='upper right', percent_change=False, line_width=10, year_over_year=False, periods_in_year=None):
    """
    Fetches and plots multiple FRED or BLS series on the same graph with vertical lines from each data point to the x-axis.
    
    Parameters:
    - series_dict: Dictionary where keys are series IDs and values are the source ('FRED' or 'BLS')
    - title: The title of the plot
    - legend_text_generator: A list that provides custom text for the legend for each series
    - from_date: The starting date for the series (default is '2000-01-01')
    - x_label: The label for the x-axis (default is 'Date')
    - y_label: The label for the y-axis (default is 'Series Value')
    """
    # Initialize an empty DataFrame for merging
    merged_df = pd.DataFrame()

    # Fetch each series based on its source (FRED or BLS) and merge into the DataFrame
    for idx, (series_id, source) in enumerate(series_dict.items()):
        if source == 'FRED':
            try:
                data = fred.get_series(series_id)
            except Exception as e:
                raise ValueError(f"Error fetching FRED series {series_id}: {e}")
        elif source == 'BLS':
            try:
                unformatted_data = get_series(series_id)  # Assuming get_series fetches BLS data

                # Convert the BLS data into a format similar to FRED (pandas Series with Date as index)
                x = unformatted_data.index.to_timestamp()
                y = unformatted_data.values
                data = pd.Series(y, index=x)
            except Exception as e:
                raise ValueError(f"Error fetching BLS series {series_id}: {e}")
        else:
            raise ValueError(f"Invalid source '{source}' for series {series_id}. Use 'FRED' or 'BLS'.")

        # Create DataFrame from the fetched data
        df = pd.DataFrame(data, columns=[f"Value_{idx}"])
        df['Date'] = df.index
        df = df[df['Date'] >= from_date]  # Filter from the specified date onwards

        # Merge with the main DataFrame on 'Date'
        if merged_df.empty:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on="Date", how="inner")

    # If frequency is not inferred, use median difference
    median_diff = merged_df['Date'].diff().median()
    st.write("Periods in year user inputted " + str(periods_in_year))
    periods_in_year_calc = round(pd.Timedelta('365 days') / median_diff)
    st.write("Periods in year calculated " + str(periods_in_year))

    if periods_in_year is None:
        periods_in_year = periods_in_year_calc

    # If change_in is True, calculate either diff or percentage change
    if change_in:
        if percent_change:
            for idx in range(len(series_dict)):
                merged_df[f'Value_{idx}'] = merged_df[f'Value_{idx}'].pct_change() * 100
        else:
            for idx in range(len(series_dict)):
                merged_df[f'Value_{idx}'] = merged_df[f'Value_{idx}'].diff()

    # If year_over_year is True, calculate YoY percentage change
    if year_over_year:
        st.write("Periods in year " + str(periods_in_year))
        for idx in range(len(series_dict)):
            merged_df[f'Value_{idx}'] = merged_df[f'Value_{idx}'].pct_change(int(periods_in_year)) * 100

    # Set up the style using seaborn
    sns.set(style="whitegrid", palette="dark")

    # Create a figure and axis with a larger size for better aesthetics
    plt.figure(figsize=(12, 8))

    custom_legend = []

    # Plot each series
    for idx in range(len(series_dict)):
        # Plot the main line for each series
        # plot_type(x='Date', y=f'Value_{idx}', data=merged_df, label=legend_text_generator[idx], linewidth=2)
        
        # Add vertical lines from each data point to the x-axis (y=0)
        plt.vlines(merged_df['Date'], ymin=0, ymax=merged_df[f'Value_{idx}'], color='blue', alpha=0.6, linewidth=line_width)
        custom_legend.append(Line2D([0], [0], color='blue', lw=line_width, label=legend_text_generator[idx]))

    # Enhance the title and labels
    plt.title(title, fontsize=18, weight='bold', color='#333333')
    plt.xlabel(x_label, fontsize=14, weight='bold', color='#333333')
    plt.ylabel(y_label, fontsize=14, weight='bold', color='#333333')

    # Rotate the x-axis labels for better readability and adjust their size
    plt.xticks(rotation=0, fontsize=12)
    plt.yticks(fontsize=12)

    # Add a grid with more customization
    plt.grid(True, linestyle='--', linewidth=0.6, alpha=0.7)

    # Show the legend with a custom location and background
    custom_legend = [Line2D([0], [0], color='blue', lw=1, label=legend_text_generator[0])]

    # Extend the existing legend
    plt.legend(handles=custom_legend, loc=legend_loc, fontsize=12, fancybox=True, shadow=True)

    # Check which source it has
    if 'FRED' in series_dict.values() and 'BLS' in series_dict.values():
        # Add a footer with the source of the data
        plt.figtext(0.27, 0, 'Source: Federal Reserve Economic Data and U.S. Bureau of Labor Statistics', ha="center", fontsize=12, style='italic')
    elif 'FRED' in series_dict.values():
        # Add a footer with the source of the data
        plt.figtext(0.17, 0, 'Source: Federal Reserve Economic Data', ha="center", fontsize=12, style='italic')
    else:
        # Add a footer with the source of the data
        plt.figtext(0.17, 0, 'Source: U.S. Bureau of Labor Statistics', ha="center", fontsize=12, style='italic')
    
    # Tighten layout to make the plot look cleaner
    plt.tight_layout()

    # Display the plot
    st.pyplot(plt)

# Streamlit app
st.title("Economic Bar Plotter")

# User input for series
st.sidebar.header("Series Input")
num_series = st.sidebar.number_input("Number of series to plot", min_value=1, max_value=10, value=1)
series_dict = {}
legend_text_generator = []

for i in range(num_series):
    series_id = st.sidebar.text_input(f"Series ID {i+1}", value=f"SAMPLE_SERIES_{i+1}")
    source = st.sidebar.selectbox(f"Source for Series {i+1}", options=["FRED", "BLS"], key=f"source_{i+1}")
    legend_text = st.sidebar.text_input(f"Legend text for Series {i+1}", value=f"Series {i+1}")
    series_dict[series_id] = source
    legend_text_generator.append(legend_text)

# Other inputs
title = st.text_input("Plot Title", value="Economic Data Plot")
from_date = st.date_input("From Date", value=pd.to_datetime("2000-01-01"))
x_label = st.text_input("X-axis Label", value="Date")
y_label = st.text_input("Y-axis Label", value="Series Value")
custom_text = st.text_input("Custom Source Text", value="Source: Federal Reserve Economic Data")
change_in = st.checkbox("Show Change in Values", value=False)
percent_change = st.checkbox("Show Percent Change", value=False)
year_over_year = st.checkbox("Year Over Year Change", value=False)
legend_loc = st.selectbox("Legend Location", options=["upper right", "upper left", "lower right", "lower left"])
periods_in_year = st.number_input("Periods in Year", min_value=0, max_value=52, value=12)
line_width = st.number_input("Bar Width", min_value=1, max_value=50, value=10)

# Generate plot
if st.button("Plot Series"):
    if percent_change and year_over_year:
        st.error("Please select only one of 'Percent Change' or 'Year Over Year Change'.")
    
    if periods_in_year == 0: periods_in_year = None

    plot_series_with_vlines(
        series_dict=series_dict, 
        title=title, 
        legend_text_generator=legend_text_generator,
        from_date=str(from_date), 
        x_label=x_label, 
        y_label=y_label, 
        change_in=change_in, 
        legend_loc=legend_loc, 
        percent_change=percent_change, 
        year_over_year=year_over_year,
        periods_in_year=periods_in_year,
        line_width=line_width
    )