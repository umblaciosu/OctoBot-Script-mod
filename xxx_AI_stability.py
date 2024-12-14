import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def fetch_historical_data(symbol="ETHUSDT", interval="1d", start_time=None, end_time=None):
    """Fetch historical price data from Binance API"""
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 1000,  # Maximum allowed by Binance API
        "startTime": start_time,
        "endTime": end_time
    }
    response = requests.get(url, params=params)
    data = response.json()
    # Parse the data into a DataFrame
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", 
        "close_time", "quote_asset_volume", "number_of_trades", 
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df[["timestamp", "close"]]

def fetch_all_data_until(symbol="TWTUSDT", interval="1d", start_date="2019-01-01"):
    """Fetch all data until a specific start date"""
    end_time = int(datetime.now().timestamp() * 1000)  # Current time in milliseconds
    start_time = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    all_data = []

    while True:
        df = fetch_historical_data(symbol=symbol, interval=interval, end_time=end_time)
        if df.empty:
            break
        all_data.append(df)
        end_time = int(df.iloc[0]["timestamp"].timestamp() * 1000) - 1  # Move back one millisecond
        if end_time <= start_time:
            break
    
    full_data = pd.concat(all_data, ignore_index=True)
    return full_data[full_data["timestamp"] >= datetime.strptime(start_date, "%Y-%m-%d")]

# Fetch all data until 2019
data = fetch_all_data_until(symbol="UNIUSDT", start_date="2019-01-01")

# Find stability intervals
def find_stability_intervals(prices, window=30, threshold=0.05):
    """Find intervals of stability based on percentage change"""
    stable_intervals = []
    for start in range(len(prices) - window + 1):
        window_prices = prices[start:start + window]
        pct_change = (max(window_prices) - min(window_prices)) / min(window_prices)
        if pct_change <= threshold:
            stable_intervals.append((start, start + window - 1))
    return stable_intervals

prices = data["close"].values
window = 45  # days
threshold = 0.16  # 5% change
stable_intervals = find_stability_intervals(prices, window=window, threshold=threshold)

# Output results
print("Stable intervals (start_idx, end_idx):")
for interval in stable_intervals:
    start_date = data.iloc[interval[0]]["timestamp"]
    end_date = data.iloc[interval[1]]["timestamp"]
    print(f"{start_date} to {end_date}")
