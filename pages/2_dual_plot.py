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

# Function to plot scatter plot using FRED or BLS data
def plot_scatter(series_dict, title, from_date='2000-01-01', x_label='Unemployment Rate', 
                 y_label='Vacancy Rate', year_cutoff=2022, legend_loc='upper right', custom_text='Source: Federal Reserve Economic Data'):
    # Initialize an empty DataFrame for merging
    merged_df = pd.DataFrame()

    # Fetch each series (vacancy and unemployment) based on its source (FRED or BLS)
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

    # Split the data by year
    merged_df['Year'] = pd.DatetimeIndex(merged_df['Date']).year

    # Set up the style using seaborn
    sns.set(style="whitegrid", palette="dark")

    # Create a figure and axis
    plt.figure(figsize=(12, 8))

    # Plot before and after the cutoff year using different colors
    before_cutoff = merged_df[merged_df['Year'] < year_cutoff]
    after_cutoff = merged_df[merged_df['Year'] >= year_cutoff]

    # Plot the points before the cutoff
    plt.scatter(before_cutoff[f'Value_0'], before_cutoff[f'Value_1'], label=f'Before {year_cutoff}', color='gray', alpha=0.6)

    # Plot the points after the cutoff with a color gradient
    unique_years = after_cutoff['Year'].unique()
    colors = sns.color_palette("dark", len(unique_years))

    for idx in range(0, len(unique_years), 2):
        year = int(unique_years[idx])
        year_data = after_cutoff[after_cutoff['Year'] == year] 
        plt.scatter(year_data[f'Value_0'], year_data[f'Value_1'], label=f'{year} - {year + 1 if year != 2024 else "Present"}', color=colors[int(idx / 2)])
        year_data = after_cutoff[after_cutoff['Year'] == year + 1] 
        plt.scatter(year_data[f'Value_0'], year_data[f'Value_1'], color=colors[int(idx / 2)])

    # Add labels and title
    plt.title(title, fontsize=18, weight='bold', color='#333333')
    plt.xlabel(x_label, fontsize=14, weight='bold', color='#333333')
    plt.ylabel(y_label, fontsize=14, weight='bold', color='#333333')

    # Rotate x-axis labels for better readability
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)

    # Add a grid
    plt.grid(True, linestyle='--', linewidth=0.6, alpha=0.7)

    # Add a legend
    plt.legend(loc=legend_loc, frameon=True, fontsize=12, fancybox=True, shadow=True)

    # Add a footer with source information
    plt.figtext(0.2, 0.02, custom_text, ha="center", fontsize=12, style='italic')

    # Display the plot
    st.pyplot(plt)

# Streamlit app
st.title("Economic Scatter Plotter")

# User input for series
st.sidebar.header("Series Input")
num_series = 2
series_dict = {}

for i in range(num_series):
    series_id = st.sidebar.text_input(f"Series ID {i+1}", value=f"SAMPLE_SERIES_{i+1}")
    source = st.sidebar.selectbox(f"Source for Series {i+1}", options=["FRED", "BLS"], key=f"source_{i+1}")
    series_dict[series_id] = source

# Other inputs
title = st.text_input("Plot Title", value="Economic Data Plot")
from_date = st.date_input("From Date", value=pd.to_datetime("2000-01-01"))
x_label = st.text_input("X-axis Label", value="Date")
y_label = st.text_input("Y-axis Label", value="Series Value")
custom_text = st.text_input("Custom Source Text", value="Source: Federal Reserve Economic Data")
legend_loc = st.selectbox("Legend Location", options=["upper right", "upper left", "lower right", "lower left"])
ignore_year = st.number_input("Ignore Years Before", min_value=2000, max_value=2022, value=2020)

# Generate plot
if st.button("Plot Series"):
    plot_scatter(
        series_dict=series_dict, 
        title=title, 
        from_date=str(from_date), 
        x_label=x_label, 
        y_label=y_label, 
        legend_loc=legend_loc,  
        custom_text=custom_text,
        year_cutoff=ignore_year
    )