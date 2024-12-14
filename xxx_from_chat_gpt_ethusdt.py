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
        "limit": 1000,  # Maximum limit per request
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

def fetch_all_historical_data(symbol="ETHUSDT", interval="1d", start_year=2019):
    """Fetch all historical data until the current date, starting from start_year"""
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int(datetime(start_year, 1, 1).timestamp() * 1000)
    all_data = []

    while start_time < end_time:
        data = fetch_historical_data(symbol, interval, start_time=start_time, end_time=end_time)
        if data.empty:
            break
        all_data.append(data)
        start_time = int(data.iloc[-1]["timestamp"].timestamp() * 1000) + 1  # Increment to avoid overlap

    return pd.concat(all_data).reset_index(drop=True)

def find_stability_intervals(prices, window=45, threshold=0.15):
    """Find intervals of stability based on percentage change"""
    stable_intervals = []
    for start in range(len(prices) - window + 1):
        window_prices = prices[start:start + window]
        pct_change = (max(window_prices) - min(window_prices)) / min(window_prices)
        if pct_change <= threshold:
            stable_intervals.append((start, start + window - 1))
    return stable_intervals

def simulate_trades(data, intervals, budget=10000, take_profit=0.25, stop_loss=-0.15):
    """Simulate trades based on stability intervals"""
    results = []
    total_profit = 0
    total_loss = 0

    for start_idx, end_idx in intervals:
        max_price = data.iloc[start_idx:end_idx + 1]["close"].max()
        min_price = data.iloc[start_idx:end_idx + 1]["close"].min()

        # Check price action after the interval
        for idx in range(end_idx + 1, len(data)):
            current_price = data.iloc[idx]["close"]

            # If price exceeds the maximum of the interval
            if current_price > max_price:
                buy_price = current_price

                # Determine order size (between 2% and 5% of the budget)
                order_size = budget * np.random.uniform(0.02, 0.05)
                tp_price = buy_price * (1 + take_profit)
                sl_price = buy_price * (1 + stop_loss)

                # Simulate trade from this point forward
                for j in range(idx + 1, len(data)):
                    future_price = data.iloc[j]["close"]
                    if future_price >= tp_price:
                        profit = (tp_price - buy_price) * (order_size / buy_price)
                        total_profit += profit
                        results.append({
                            "buy_date": data.iloc[idx]["timestamp"],
                            "sell_date": data.iloc[j]["timestamp"],
                            "buy_price": buy_price,
                            "sell_price": tp_price,
                            "result": "Take Profit",
                            "profit": profit
                        })
                        break
                    elif future_price <= sl_price:
                        loss = (buy_price - sl_price) * (order_size / buy_price)
                        total_loss += loss
                        results.append({
                            "buy_date": data.iloc[idx]["timestamp"],
                            "sell_date": data.iloc[j]["timestamp"],
                            "buy_price": buy_price,
                            "sell_price": sl_price,
                            "result": "Stop Loss",
                            "loss": loss
                        })
                        break

                # Additional buy order with different TP/SL
                extended_tp_price = buy_price * 1.5
                extended_sl_price = buy_price * 0.65

                for k in range(idx + 1, len(data)):
                    future_price = data.iloc[k]["close"]
                    if future_price >= extended_tp_price:
                        profit = (extended_tp_price - buy_price) * (order_size / buy_price)
                        total_profit += profit
                        results.append({
                            "buy_date": data.iloc[idx]["timestamp"],
                            "sell_date": data.iloc[k]["timestamp"],
                            "buy_price": buy_price,
                            "sell_price": extended_tp_price,
                            "result": "Extended Take Profit",
                            "profit": profit
                        })
                        break
                    elif future_price <= extended_sl_price:
                        loss = (buy_price - extended_sl_price) * (order_size / buy_price)
                        total_loss += loss
                        results.append({
                            "buy_date": data.iloc[idx]["timestamp"],
                            "sell_date": data.iloc[k]["timestamp"],
                            "buy_price": buy_price,
                            "sell_price": extended_sl_price,
                            "result": "Extended Stop Loss",
                            "loss": loss
                        })
                        break
                break  # Only consider the first condition met

            # If price drops below the minimum of the interval
            elif current_price < min_price:
                break

    return pd.DataFrame(results), total_profit, total_loss

# Fetch all historical data starting from 2019
data = fetch_all_historical_data(symbol="ETHUSDT", interval="1d", start_year=2019)

# Identify stable intervals
stable_intervals = find_stability_intervals(data["close"].values, window=45, threshold=0.15)

# Simulate trades based on stability intervals
trade_results, total_profit, total_loss = simulate_trades(data, stable_intervals)

# Output trade results
print(trade_results)
print(f"Total Profit: {total_profit}")
print(f"Total Loss: {total_loss}")
