from flask import Flask, render_template, request, redirect, url_for
import requests
import pandas as pd
import plotly
import plotly.express as px
import json
import os

app = Flask(__name__)

# Alpha Vantage API key
API_KEY = "Z44DR7L1TCPO0BOR"
BASE_URL = "https://www.alphavantage.co/query"

# Load stock symbols from CSV
def get_stock_symbols():
    symbols = []
    try:
        df = pd.read_csv('stocks.csv')
        symbols = df['Symbol'].tolist()  # Adjust column name as needed
    except FileNotFoundError:
        # Fallback to common stocks if CSV not found
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ',
                   'BRK-B', 'UNH', 'JNJ', 'XOM', 'PG', 'MA', 'CVX', 'LLY', 'HD', 'MRK',
                   'ABBV', 'PFE', 'BAC', 'KO', 'PEP', 'COST', 'TMO', 'AVGO', 'ABT', 'ACN',
                   'WMT', 'DHR', 'CRM', 'NEE', 'VZ', 'NKE', 'ADBE', 'CMCSA', 'MDT', 'TXN',
                   'UNP', 'LIN', 'RTX', 'BMY', 'QCOM', 'HON', 'INTU', 'AMGN', 'LOW', 'SBUX',
                   'BA', 'ISRG', 'CAT', 'GS', 'SPGI', 'BLK', 'AXP', 'DE', 'MMM', 'NOW',
                   'SYK', 'TJX', 'BKNG', 'GILD', 'ADI', 'MDLZ', 'CVS', 'CI', 'MO', 'ZTS',
                   'SCHW', 'TMUS', 'CB', 'SO', 'DUK', 'BDX', 'MS', 'PLD', 'USB', 'CL',
                   'T', 'AEP', 'EOG', 'ITW', 'NSC', 'APD', 'ICE', 'SHW', 'F', 'GM',
                   'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'NXPI', 'CDNS', 'SNPS', 'MCHP',
                   'FTNT', 'ADSK', 'WDAY', 'PANW', 'CRWD', 'SNOW', 'DDOG', 'NET', 'ZS',
                   'TEAM', 'SHOP', 'SQ', 'PYPL', 'V', 'MA', 'JPM', 'BAC', 'WFC', 'C',
                   'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'BRK-B', 'JNJ', 'UNH', 'PFE', 'ABBV',
                   'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY', 'AMGN', 'GILD', 'MDT', 'ISRG',
                   'SYK', 'ZTS', 'VRTX', 'REGN', 'BIIB', 'ILMN', 'MRNA', 'BNTX', 'PFE',
                   'JNJ', 'UNH', 'CVS', 'CI', 'HUM', 'ANTM', 'CNC', 'MOH', 'ELV', 'HCA',
                   'UHS', 'THC', 'LPNT', 'ACHC', 'SEM', 'AMED', 'ENSG', 'CLOV', 'DOCS',
                   'PODD', 'DXCM', 'ISRG', 'ZBH', 'SYK', 'ALGN', 'BAX', 'BDX', 'MMSI',
                   'NVST', 'PODD', 'HOLX', 'TFX', 'RMD', 'DXCM', 'ALGN', 'NVST', 'PODD',
                   'HOLX', 'TFX', 'RMD']
    return symbols

def get_stock_data(symbol, function, interval=None):
    parameters = {
        "function": function,
        "symbol": symbol,
        "outputsize": "full",
        "apikey": API_KEY
    }

    if function == "TIME_SERIES_INTRADAY":
        parameters["interval"] = interval

    try:
        response = requests.get(
            url=BASE_URL,
            params=parameters,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        print("Error connecting to Alpha Vantage:", error)
        return None

    if "Error Message" in data:
        print("API Error:", data["Error Message"])
        return None
    
    if "Note" in data:
        print("API limit message:", data["Note"])
        return None

    if "Information" in data:
        print("API Information", data["Information"])
        return None

    time_series_key = next(
        (key for key in data if "Time Series" in key),
        None
    )

    if time_series_key is None:
        print("No stock data was returned.")
        return None

    df = pd.DataFrame.from_dict(
        data[time_series_key],
        orient="index"
    )

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df.columns = [
        column.split(". ", 1)[-1].lower()
        for column in df.columns
    ]

    for column in df.columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df

def filter_dates(df, start_date, end_date):
    mask = (df.index >= start_date) & (df.index <= end_date)
    return df.loc[mask]

def create_chart(df, symbol, chart_type, start_date, end_date):
    if df.empty:
        print("No stock data available to create a chart.")
        return None

    if "close" not in df.columns:
        print("No closing prices found.")
        return None

    title = f"{symbol} Stock Prices ({start_date} to {end_date})"

    if chart_type == "Bar":
        chart = px.bar(df, x=df.index, y="close", title=title)
    elif chart_type == "Line":
        chart = px.line(df, x=df.index, y="close", title=title)
    else:
        print("Invalid chart type.")
        return None

    chart.update_layout(
        xaxis_title="Date",
        yaxis_title="Closing Price ($)"
    )

    return chart

@app.route('/', methods=['GET', 'POST'])
def index():
    symbols = get_stock_symbols()
    chart_html = None
    error_message = None
    
    if request.method == 'POST':
        try:
            symbol = request.form.get('stock_symbol', '').strip().upper()
            chart_type = request.form.get('chart_type')
            function_choice = request.form.get('time_series')
            interval = request.form.get('interval')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            if not symbol:
                error_message = "Please enter a stock symbol"
            elif not chart_type:
                error_message = "Please select a chart type"
            elif not function_choice:
                error_message = "Please select a time series type"
            elif function_choice == "TIME_SERIES_INTRADAY" and not interval:
                error_message = "Please select an intraday interval"
            elif not start_date or not end_date:
                error_message = "Please select start and end dates"
            else:
                # Map form choices to functions
                functions = {
                    "1": "TIME_SERIES_INTRADAY",
                    "2": "TIME_SERIES_DAILY",
                    "3": "TIME_SERIES_WEEKLY",
                    "4": "TIME_SERIES_MONTHLY"
                }
                
                function = functions.get(function_choice)
                
                if function == "TIME_SERIES_INTRADAY":
                    intervals = {
                        "1": "1min",
                        "2": "5min",
                        "3": "15min",
                        "4": "30min",
                        "5": "60min",
                    }
                    interval = intervals.get(interval)
                
                # Get stock data
                stock_data = get_stock_data(symbol, function, interval)
                
                if stock_data is None:
                    error_message = "Failed to retrieve stock data. Please try again."
                else:
                    # Filter dates
                    filtered_data = filter_dates(stock_data, start_date, end_date)
                    
                    if filtered_data.empty:
                        error_message = "No data available for the selected date range."
                    else:
                        # Create chart
                        chart = create_chart(filtered_data, symbol, chart_type, start_date, end_date)
                        
                        if chart:
                            chart_html = plotly.io.to_html(chart, full_html=False)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
    
    return render_template('index.html', 
                         symbols=symbols, 
                         chart_html=chart_html, 
                         error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)
