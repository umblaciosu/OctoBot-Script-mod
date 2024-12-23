import asyncio
import tulipy     # Can be any TA library.
import octobot_script as obs
import numpy as np
import pandas as pd
import talib as tl
import matplotlib.pyplot as plt
import time
from datetime import datetime

#--------------------------INPUTS--------------------------------
global closes
global times
global volume

global medie_close
global medie_volum
global interval_stabil_flag
interval_stabil_flag = False
interval_stabil_final=[]
global counter_strategy_run
counter_strategy_run = 0

IS_length_min = 20  # nr pozitii minime intre varfuri
interval_stabil = 150

proc_intre_vrf_line_IS = 0.1  #(2%)
pr_vrf_dif_medie = 0.025  #(2.5%)
procent_spargere_IS = 0.05  #(5%)

procent_volum_max = 0.3 # (80%)  # volume mari pe buy [only]
procent_high_close_cross = 0.3 # (20% diferenta intre ele)
var_nr_volume = 3  #cate volume mari sa fie in IS
medie_close_period = 7

cross_max = 0
cross_min = 0
crossed = False
wider_line_max = False
wider_line_min = False

# Array to store local maxima
line_max = []
line_min = []

#global variables
global high
global low
global times
global volume

smma = [0]
sb = []

# MACD Section
lengthMA = 34
lengthSignal = 9
macd_max_delta = 0.18

#--------------------------FUNCTIONS------------------------------
async def calc_smma(src: np.ndarray, length: int) -> np.ndarray:
    """
    Calculate Smoothed Moving Average (SMMA) for a given numpy array `src` with a specified `length`.

    :param src: A numpy ndarray of shape (n,) containing the input values of float64 dtype.
    :param length: An integer representing the length of the SMMA window.
    :return: A numpy ndarray of the same shape as `src` containing the SMMA values.
    """
    smma = np.full_like(src, fill_value=np.nan)
    sma = tl.SMA(src, length)

    for i in range(1, len(src)):
        smma[i] = (
            sma[i]
            if np.isnan(smma[i - 1])
            else (smma[i - 1] * (length - 1) + src[i]) / length
        )

    return smma

async def calc_zlema(src: np.ndarray, length: int) -> np.ndarray:
    """
    Calculates the zero-lag exponential moving average (ZLEMA) of the given price series.

    :param src: The input price series of float64 dtype to calculate the ZLEMA for.
    :param length: int The number of bars to use for the calculation of the ZLEMA.
    :return: A numpy ndarray of ZLEMA values for the input price series.
    """
    ema1 = tl.EMA(src, length)
    ema2 = tl.EMA(ema1, length)
    d = ema1 - ema2
    return ema1 + d

def find_last(list: list,counter: int):
    #find the last element from the current position: counter to 0.
    if counter < 2:
        return 0
    else:
        for i in range(1,counter):
            if list[counter-i] > 0:
                return list[counter-i]
            else:
                continue

async def macd_improved(high, low, hlc3):
    #Start of MACD
    src=hlc3
    hi= await calc_smma(high, lengthMA)
    lo= await calc_smma(low, lengthMA)
    mi= await calc_zlema(src, lengthMA)

    md = np.full_like(mi, fill_value=np.nan)

    conditions = [mi > hi, mi < lo]
    choices = [mi - hi, mi - lo]

    md = np.select(conditions, choices, default=0)

    sb = tulipy.sma(md, lengthSignal)        #"ImpulseMACDCDSignal": sb
    md = md[md.size-sb.size:]                #"ImpulseMACD": md
    sh = md - sb                             #"ImpulseHisto": sh
    #end of MACD
    return [sb,md,sh]

async def find_valid_pairs(closes, high, low, data, time_series, max_diff_fraction, isMax):
    """
    Find all pairs (i, j) in the list `data` such that:
    1. Both elements are non-zero.
    2. The difference between the values is no more than max_diff_fraction% [ 0.1 for 10% ] of the smaller value.
    3a. If isMax is True All values between the indices of the pair are less than or equal to the larger value of the pair.
    3b. If isMax is False All values between the indices of the pair are higher than or equal to the lower value of the pair.
    
    Parameters:
        data (list): List of integers.
    
    Returns:
        list: A list of tuples, where each tuple contains the indices and values of the valid pairs.
    """
    pairs = []
    n = len(data)
    
    for i in range(n):
        for j in range(i + 1, n):
            a, b = data[i], data[j]
            
            # Both values must be non-zero
            if a == 0 or b == 0:
                continue
            
            # Check the max_diff_fraction(%) difference condition
            if abs(a - b) > max_diff_fraction * min(a, b):
                continue
            
            # Case max_value interval - check if there is a greater value between the pairs
            # Check if 
            flag = False
            if isMax == True:
                for k in range(i + 1, j):
                    c = closes[k]
                    # if c == 1729.42:
                    #     print("this!")
                    # if b == 163.31:
                    #     print("that!")
                    if c > a or c > b:
                        flag = True
                        break
            else:
            # Case min_value interval - check if there is a lower value between the pairs
                for k in range(i + 1, j):
                    if closes[k] < a or closes[k] < b:
                        flag = True
                        break
                    
            if flag == False and abs(i-j) >= int(IS_length_min):
                best_result = {
                        "start_time": time_series[i],
                        "human_start_time": datetime.fromtimestamp(time_series[i]).strftime('%Y-%m-%d'),
                        "start_price": a,
                        "end_time": time_series[j],
                        "human_end_time": datetime.fromtimestamp(time_series[j]).strftime('%Y-%m-%d'),
                        "end_price": b,
                    }
                pairs.append(best_result)
    return pairs

# Function to find the maximum overlapping interval with the smallest price difference
def find_max_overlap_with_price(maximum_list, minimum_list, closes, times):
    # Function to find the overlap between two intervals
    def overlap(interval1, interval2):
        start = max(interval1["start_time"], interval2["start_time"])
        end = min(interval1["end_time"], interval2["end_time"])
        if start < end and end - start > 86400*IS_length_min/3: #a  minimum overlap
            return  {
                        "start_time": start,
                        "human_start_time": datetime.fromtimestamp(start).strftime('%Y-%m-%d'),
                        "end_time": end,
                        "human_end_time": datetime.fromtimestamp(end).strftime('%Y-%m-%d'),
                    }
        return None  # No overlap

    max_overlap = 0
    min_price_difference = float('inf')
    best_result = None

    # Compare every interval in maximum_list with every interval in minimum_list
    for max_interval in maximum_list:
        for min_interval in minimum_list:
            overlapping_interval = overlap(max_interval, min_interval)

            if overlapping_interval:
                #### find if between start interval and end interval if closes > max or closes < min
                time_start = overlapping_interval["start_time"]
                index_start = times.index(time_start)
                time_end = max(max_interval["end_time"], min_interval["end_time"])
                index_end = times.index(time_end)
                #for i in range(index_start+1,index_end):
                for i in closes[index_start+1:index_end]:
                    if i > ( max_interval["start_price"] + max_interval["end_price"] ) / 2:
                        return None
                    else:
                        if i < ( min_interval["start_price"] + min_interval["end_price"] ) / 2:
                            return None
                overlap_start, overlap_end = overlapping_interval["start_time"],overlapping_interval["end_time"]
                overlap_duration = overlap_end - overlap_start

                # Update best interval if the overlap duration is larger or price difference is smaller
                if (overlap_duration > max_overlap) or (
                    overlap_duration == max_overlap ):
                    max_overlap = overlap_duration
                    best_result = {
                        "max_int_start_Htime": max_interval["human_start_time"],
                        "max_int_start_time": max_interval["start_time"],
                        "max_int_start_price": max_interval["start_price"],
                        "max_int_end_Htime": max_interval["human_end_time"],
                        "max_int_end_time": max_interval["end_time"],
                        "max_int_end_price": max_interval["end_price"],
                        "min_int_start_Htime": min_interval["human_start_time"],
                        "min_int_start_time": min_interval["start_time"],
                        "min_int_start_price": min_interval["start_price"],
                        "min_int_end_Htime": min_interval["human_end_time"],
                        "min_int_end_time": min_interval["end_time"],
                        "min_int_end_price": min_interval["end_price"],
                    }
    return best_result

async def define_stability_interval(closes, high, low, times, volume,ctx):
        # Will be called at each candle.
    interval_stabilitate = False
    global sb
    global max_pairs
    global min_pairs
    local_maxim = []
    local_minim = []

    hlc3 = (high + low + closes)/3

    medie_close = tulipy.sma(closes, medie_close_period)
    medie_volum = tulipy.sma(volume, 35)

    #Start of MACD
    src=hlc3
    hi= await calc_smma(high, lengthMA) #needs smma !!! --------
    lo= await calc_smma(low, lengthMA) #needs smma !!! --------
    mi= await calc_zlema(src, lengthMA) # needs smma !!! -------

    md = np.full_like(mi, fill_value=np.nan)

    conditions = [mi > hi, mi < lo]
    choices = [mi - hi, mi - lo]

    md = np.select(conditions, choices, default=0)

    sb,md,sh = await macd_improved(high,low,hlc3)

    #reset local_maxim, and local_minim --> to be improved -> sliding window ?!
    #local_maxim.clear()
    #local_minim.clear()

    #prepare length for local_maxim and local_minim
    for i in range(medie_close_period):
        local_maxim.append(0)
        local_minim.append(0)
    
    for i in range(medie_close_period,len(closes)-1):
        if closes[i-1] < closes[i] and closes[i] > closes[i+1]:
            if closes[i] / medie_close[i-medie_close_period] >= 1 + pr_vrf_dif_medie:
                local_maxim.append(closes[i])
            else:
                local_maxim.append(0)
        else:
            local_maxim.append(0)
    local_maxim.append(0) ### To be optimized

    #Build the local_minim list
    for i in range(medie_close_period,len(closes)-1):
        if closes[i-1] > closes[i] and closes[i] < closes[i+1]:
            if closes[i] / medie_close[i-medie_close_period] <= 1 - pr_vrf_dif_medie:
                local_minim.append(closes[i])
            else:
                local_minim.append(0)
        else:
            local_minim.append(0)
    local_minim.append(0) ### To be optimized

    #await obs.plot_indicator(ctx, "Local_Maxim", times[delta:], local_maxim, run_data["entries"])
    #await obs.plot_indicator(ctx, "Local_Maxim2", times[delta:], local_maxim, run_data["entries2"])
    await obs.plot(ctx, "Medie_close", times[:], medie_close, mode="lines",color="blue")
    await obs.plot(ctx, "Local_maxim", times[:], local_maxim, mode="lines",color="white")
    await obs.plot(ctx, "Local_minim", times[:], local_minim, mode="lines",color="green")

    #plt.plot(medie_close,times[:len(medie_close)],local_maxim,times[:len(medie_close)],local_minim,times[:len(medie_close)])
    #plt.show()

    ### PRINT MACD
    await obs.plot(ctx, "ImpulseMACD", times[:], md, mode="scatter",color="blue", chart="main-chart")
    await obs.plot(ctx, "ImpulseHisto", times[:], sh, mode="scatter",color="white", chart="main-chart")
    await obs.plot(ctx, "ImpulseMACDCDSignal", times[:], sb, mode="lines",color="green", chart="main-chart")

    max_pairs = await find_valid_pairs(closes, high, low, local_maxim, times[:len(local_maxim)], proc_intre_vrf_line_IS, True)
    min_pairs = await find_valid_pairs(closes, high, low, local_minim, times[:len(local_minim)], proc_intre_vrf_line_IS, False)

    best_result = find_max_overlap_with_price(max_pairs, min_pairs, closes, times)

    return best_result

def analyze_the_break(last_closes, last_high, last_low, last_times, interval_stabil_local):
    # Check if closes breaks the stability interval
    if last_closes > (interval_stabil_local["max_int_start_price"]+interval_stabil_local["max_int_end_price"]) / 2:
        # check if the high/close ratio is good ( no more than procent_high_close_cross % )
        if ( last_closes - last_low ) / ( last_high - last_low ) > 1 - procent_high_close_cross:
            return True
    else:
        # check if it breaks the lower interval
        if last_closes < (interval_stabil_local["min_int_start_price"]+interval_stabil_local["min_int_end_price"]) / 2:
            return False
        else:
            return None
    
async def stability_interval():   
    global interval_stabil_final

    async def strategy(ctx):
        global interval_stabil_final
        global interval_stabil_flag
        if run_data["entries"] is None:
            # Compute entries only once per backtest.
            times_global = await obs.Time(ctx, max_history=True, use_close_time=True)
        
        closes = await obs.Close(ctx)
        high = await obs.High(ctx)
        low = await obs.Low(ctx)
        times = await obs.Time(ctx, use_close_time=True)
        volume = await obs.Volume(ctx)
        
        if len(closes) < interval_stabil:
            return
        else:
            if interval_stabil_flag == False:
                result1 = await define_stability_interval(closes[-interval_stabil:], high[-interval_stabil:], low[-interval_stabil:], times[-interval_stabil:], volume[-interval_stabil:],ctx)
                if result1 not in interval_stabil_final and result1 != None:
                    interval_stabil_flag=True
                    interval_stabil_final.append(result1)
            else:
                mod = analyze_the_break(closes[-1], high[-1], low[-1], times[-1], interval_stabil_final[-1])
                if mod == False:
                    interval_stabil_flag=False
                    print("spargere in jos!")
                else:
                    if mod == True:
                        await obs.market(ctx, "buy", amount="10%", stop_loss_offset="-15%", take_profit_offset="25%")
                        print("spargere buna!")
                        interval_stabil_flag=False

        
        if times[-1] == times_global[-1] and len(interval_stabil_final)!=0:
            #After all intervals were found - find overlapping intervals and choose the longest
            # with the lowest price diff
            
            #preparing stability intervals found for plotting
            for counter,interval in enumerate(interval_stabil_final):
                """
                Building the stability period intervals:
                -> Find index of the start interval in times_global rage
                -> start filling with 0 until start of the interval, then maximum of the values of the staiblity interval until end time
                -> then 0 until lenght of times_global
                """
                printable_interval_max = []
                printable_interval_min = []
                if times_global.index(interval["max_int_start_time"]) and times_global.index(interval["max_int_end_time"]):
                    index_max_found1 = times_global.index(interval["max_int_start_time"])
                    index_min_found1 = times_global.index(interval["min_int_start_time"])
                    #start filling printable_interval_max with 0 until max_interval found
                    for i in range(index_max_found1):
                        printable_interval_max.append(0)
                    #start filling printable_interval_min with 0 until min_interval found
                    for i in range(index_min_found1):
                        printable_interval_min.append(0)
                    
                    index_max_found2 = times_global.index(interval["max_int_end_time"])
                    index_min_found2 = times_global.index(interval["min_int_end_time"])
                    for i in range(index_max_found2-index_max_found1):
                        printable_interval_max.append((interval["max_int_start_price"]+interval["max_int_end_price"])/2)
                    #start filling printable_interval_min with 0 until min_interval found
                    for i in range(index_min_found2-index_min_found1):
                        printable_interval_min.append((interval["min_int_start_price"]+interval["min_int_end_price"])/2)
                    
                    for i in range(len(times_global)-index_max_found2):
                        printable_interval_max.append(0)
                    #start filling printable_interval_min with 0 until min_interval found
                    for i in range(len(times_global)-index_min_found2):
                        printable_interval_min.append(0)
                else:
                    print("One of the time intervals was not found for printing!")

                await obs.plot(ctx, "Interval_max"+str(counter), times_global[:], printable_interval_max, mode="scatter",color="blue", chart="main-chart")
                await obs.plot(ctx, "Interval_min"+str(counter), times_global[:], printable_interval_min, mode="scatter",color="blue", chart="main-chart")


     # Configuration that will be passed to each run.
     # It will be accessible under "ctx.tentacle.trading_config".
    config = {
        "IS_length_min": 20,  # nr pozitii minime intre varfuri
        "interval_stabil": 150,
        "proc_intre_vrf_line_IS": 0.1,  #(2%)
        "pr_vrf_dif_medie": 0.025,  #(2.5%)
        "procent_spargere_IS": 0.05,  #(5%)

        "procent_volum_max": 0.3, # (80%)  # volume mari pe buy [only]
        "procent_high_close_cross": 0.3, # (20% diferenta intre ele)
        "var_nr_volume": 3,  #cate volume mari sa fie in IS
        "max_val": 2500,
    }

     # Read and cache candle data to make subsequent backtesting runs faster.
    #datafile = "ExchangeHistoryDataCollector_1733862750.5739202.data"
    data = await obs.get_data("ETH/USDT", "1d", start_timestamp=1546300800, end_timestamp=1703980800)
    #data = await obs.get_data("ETH/USDT", "1d", data_file=datafile)

    run_data = {
        "entries": None,
    }
     # Run a backtest using the above data, strategy and configuration.
    res = await obs.run(data, strategy, config)
    
    #print("Stability Intervals found: ", interval_stabil_final)


    print(res.describe())
     # Generate and open report including indicators plots
    await res.plot(show=True)
     # Stop data to release local databases.
    await data.stop()


 # Call the execution of the script inside "asyncio.run" as
 # OctoBot-Script runs using the python asyncio framework.
asyncio.run(stability_interval())
