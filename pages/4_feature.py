import streamlit as st
import pandas as pd
import seaborn as sns, os, numpy as np
import matplotlib.pyplot as plt
from fredapi import Fred
from bls import get_series
from matplotlib.lines import Line2D
import yfinance as yf
import mpld3
import streamlit.components.v1 as components

# load APIs
from dotenv import load_dotenv
load_dotenv()

# Configure FRED and BLS API keys
API_KEY = os.getenv('FRED_API_KEY')
os.environ['BLS_API_KEY'] = os.getenv('BLS_API_KEY')

# Initialize FRED API
fred = Fred(api_key=API_KEY)

# Streamlit app
st.title("Economic Bar Plotter")

# User input for series
st.sidebar.header("Feature Input")
formula = st.sidebar.text_input("Formula", value="UNRATE + CPIAUCSL")

def fetch_series(series_id):
    # check if day, month, year, time, or constant value
    if series_id in ['DAY', 'MONTH', 'YEAR', 'TIME']:
        # create a pandas series starting from 1900-01-01 to today
        time = pd.date_range(start='1900-01-01', end=pd.Timestamp.today())
        if series_id == 'DAY':
            series = pd.Series(time.day)
        elif series_id == 'MONTH':
            series = pd.Series(time.month)
        elif series_id == 'YEAR':
            series = pd.Series(time.year)
        elif series_id == 'TIME':
            series = pd.Series(time.hour)

        # convert the series to have the 
        x = time.to_pydatetime()
        y = series.values

        return pd.Series(y, index=x)

    # Try FRED
    try:
        return fred.get_series(series_id)
    except Exception as e:
        pass
    
    # Then Try BLS
    try:
        unformatted_data = get_series(series_id)  # Assuming get_series fetches BLS data

        # Convert the BLS data into a format similar to FRED (pandas Series with Date as index)
        x = unformatted_data.index.to_timestamp()
        y = unformatted_data.values
        return pd.Series(y, index=x)
    except Exception as e:
        pass

    # Then Try Yahoo Finance
    try:
        series = yf.Ticker(series_id).history(period='max')

        x = series.index

        # convert x to datetime
        x = pd.to_datetime(x)

        y = series['Close']

        return pd.Series(y, index=x)
    except Exception as e:
        pass
    
    print(f"Invalid source for series {series_id}.")
    # return an empty series if the series ID is invalid
    return pd.Series()

def evaluate_formula(formula):
    """
    Evaluates a formula and returns the series IDs and sources.

    Parameters:
    - formula: A string representing the formula to evaluate

    Valid Operators:
    - '+' for addition
    - '-' for subtraction
    - '*' for multiplication
    - '/' for division
    - '(' and ')' for grouping
    - '^' for exponentiation
    - '|' for absolute value
    - 'log' for natural logarithm
    - 'DAY, MONTH, YEAR' for date number
    - 'TIME' for time number
    - '$' before series for constant value (the latest value)
    - Any text for FED or BLS series IDs

    Returns:
    - A series with the evaluated formula
    """
    
    def apply_operator(op, operand1, operand2=None):
        # Convert Series to have same index through forward fill
        if operand2 is not None and hasattr(operand1, 'index') and hasattr(operand2, 'index'):
            combined_index = operand1.index.union(operand2.index)
            operand1 = operand1.reindex(combined_index).ffill()
            operand2 = operand2.reindex(combined_index).ffill()
        
        if op == '|':
            return abs(operand1)
        elif op == 'log':
            return np.log(operand1)
        elif op == '+':
            return operand1 + operand2
        elif op == '-':
            return operand1 - operand2
        elif op == '*':
            return operand1 * operand2
        elif op == '/':
            return operand1 / operand2
        elif op == '^':
            return operand1 ** operand2
    
    def tokenize(formula):
        tokens = []
        current = ''
        
        for char in formula:
            if char in '+-*/^()|':
                if current:
                    tokens.append(current.strip())
                tokens.append(char)
                current = ''
            elif char.isspace():
                if current:
                    tokens.append(current.strip())
                current = ''
            else:
                current += char
        
        if current:
            tokens.append(current.strip())
            
        return tokens

    def parse_token(token):
        if token.startswith('$'):
            series = fetch_series(token[1:])
            st.write(f"{token} value {series}")
            return series.iloc[-1]
        
        try:
            return float(token)
        except ValueError:
            series = fetch_series(token)

            # plot series
            fig = plt.figure(figsize=(12, 6))
            sns.lineplot(data=series)
            plt.title(f"Series {token}")
            plt.xlabel("Date")
            plt.ylabel("Value")
            st.pyplot(fig)

            return series

    precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3, '|': 4, 'log': 4}
    tokens = tokenize(formula)
    output_queue = []
    operator_stack = []
    
    for token in tokens:
        if token in precedence:
            while (operator_stack and operator_stack[-1] != '(' and 
                   precedence[operator_stack[-1]] >= precedence[token]):
                output_queue.append(operator_stack.pop())
            operator_stack.append(token)
        elif token == '(':
            operator_stack.append(token)
        elif token == ')':
            while operator_stack and operator_stack[-1] != '(':
                output_queue.append(operator_stack.pop())
            if operator_stack and operator_stack[-1] == '(':
                operator_stack.pop()
        else:
            output_queue.append(token)
    
    while operator_stack:
        output_queue.append(operator_stack.pop())
    
    value_stack = []
    
    for token in output_queue:
        if token in precedence:
            if token in ['|', 'log']:
                operand = value_stack.pop()
                result = apply_operator(token, operand)
            else:
                operand2 = value_stack.pop()
                operand1 = value_stack.pop()
                result = apply_operator(token, operand1, operand2)
            value_stack.append(result)
        else:
            value_stack.append(parse_token(token))
    
    return value_stack[0]

if st.button("Plot Series"):
    new_series = evaluate_formula(formula)

    # Plot the series
    fig = plt.figure(figsize=(12, 6))
    sns.lineplot(data=new_series)
    plt.title(f"Evaluated Series {formula}")
    plt.xlabel("Date")
    plt.ylabel("Value")
    
    st.pyplot(fig)