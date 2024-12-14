import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from plotly.offline import plot

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
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    return df[["timestamp", "open", "high", "low", "close"]]

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
    simulated_budget = [budget]
    buy_markers = []
    sell_markers = []

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

                # Mark buy point
                buy_markers.append((data.iloc[idx]["timestamp"], buy_price))

                # Simulate trade from this point forward
                for j in range(idx + 1, len(data)):
                    future_price = data.iloc[j]["close"]
                    if future_price >= tp_price:
                        profit = (tp_price - buy_price) * (order_size / buy_price)
                        budget += profit
                        simulated_budget.append(budget)
                        total_profit += profit

                        # Mark sell point
                        sell_markers.append((data.iloc[j]["timestamp"], tp_price))

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
                        budget -= loss
                        simulated_budget.append(budget)
                        total_loss += loss

                        # Mark sell point
                        sell_markers.append((data.iloc[j]["timestamp"], sl_price))

                        results.append({
                            "buy_date": data.iloc[idx]["timestamp"],
                            "sell_date": data.iloc[j]["timestamp"],
                            "buy_price": buy_price,
                            "sell_price": sl_price,
                            "result": "Stop Loss",
                            "loss": loss
                        })
                        break
                break  # Only consider the first condition met

            # If price drops below the minimum of the interval
            elif current_price < min_price:
                break

    return pd.DataFrame(results), simulated_budget, total_profit, total_loss, buy_markers, sell_markers

def create_html_report(data, simulated_budget, trade_results, buy_markers, sell_markers):
    """Create an HTML report with the plots and trade results"""
    # Plot candles
    fig_candles = make_subplots(rows=1, cols=1)
    fig_candles.add_trace(go.Candlestick(
        x=data['timestamp'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name="Candlestick"
    ))

    # Add buy and sell markers
    for marker in buy_markers:
        fig_candles.add_trace(go.Scatter(
            x=[marker[0]],
            y=[marker[1]],
            mode="markers",
            marker=dict(color="green", size=10, symbol="triangle-up"),
            name="Buy"
        ))

    for marker in sell_markers:
        fig_candles.add_trace(go.Scatter(
            x=[marker[0]],
            y=[marker[1]],
            mode="markers",
            marker=dict(color="red", size=10, symbol="triangle-down"),
            name="Sell"
        ))

    fig_candles.update_layout(title="ETH/USDT Price Chart", xaxis_title="Date", yaxis_title="Price (USDT)")

    # Plot budget simulation
    fig_budget = make_subplots(rows=1, cols=1)
    fig_budget.add_trace(go.Scatter(
        x=data['timestamp'][:len(simulated_budget)],
        y=simulated_budget,
        mode="lines",
        name="Simulated Budget"
    ))
    fig_budget.update_layout(title="Simulated Budget Over Time", xaxis_title="Date", yaxis_title="Budget (USDT)")

    # Combine into an HTML report
    html_content = f"""<html>
    <head><title>ETH Strategy by George</title></head>
    <body>
    <h1 style='text-align: center;'>ETH Strategy by George</h1>
    <div>{plot(fig_candles, output_type='div')}</div>
    <div>{plot(fig_budget, output_type='div')}</div>
    <h2>Trade Results</h2>
    {trade_results.to_html(index=False)}
    </body>
    </html>"""

    # Save report to file
    with open("ETH_Strategy_Report.html", "w") as f:
        f.write(html_content)

# Fetch all historical data starting from 2019
data = fetch_all_historical_data(symbol="ETHUSDT", interval="1d", start_year=2019)

# Identify stable intervals
stable_intervals = find_stability_intervals(data["close"].values, window=45, threshold=0.15)

# Simulate trades based on stability intervals
trade_results, simulated_budget, total_profit, total_loss, buy_markers, sell_markers = simulate_trades(data, stable_intervals)

# Create the HTML report
create_html_report(data, simulated_budget, trade_results, buy_markers, sell_markers)

# Output summary
print("Report generated: ETH_Strategy_Report.html")
print(f"Total Profit: {total_profit}")
print(f"Total Loss: {total_loss}")
