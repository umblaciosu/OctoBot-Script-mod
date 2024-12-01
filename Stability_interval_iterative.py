import asyncio
import tulipy     # Can be any TA library.
import octobot_script as obs
import numpy as np
import pandas as pd
import talib as tl
import matplotlib.pyplot as plt

#--------------------------INPUTS--------------------------------
global closes
global times
global volume

global medie_close
global medie_volum
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
    hi= await calc_smma(high, lengthMA) #needs smma !!! --------
    lo= await calc_smma(low, lengthMA) #needs smma !!! --------
    mi= await calc_zlema(src, lengthMA) # needs smma !!! -------

    md = np.full_like(mi, fill_value=np.nan)

    conditions = [mi > hi, mi < lo]
    choices = [mi - hi, mi - lo]

    md = np.select(conditions, choices, default=0)

    sb = tulipy.sma(md, lengthSignal)        #"ImpulseMACDCDSignal": sb
    md = md[md.size-sb.size:]                #"ImpulseMACD": md
    sh = md - sb                             #"ImpulseHisto": sh
    #end of MACD
    return [sb,md,sh]

async def find_valid_pairs(data, time_series, max_diff_fraction, isMax):
    #AI generated
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
            flag = False
            if isMax == True:
                for k in range(i + 1, j):
                    if data[k] > max(a, b):
                        flag = True
                        break
            else:
            # Case min_value interval - check if there is a lower value between the pairs
                for k in range(i + 1, j):
                    if data[k] < min(a, b) and data[k]!=0:
                        flag = True
                        break
                    
            if flag == False:
                pairs.append(((time_series[i], time_series[j]), (a, b)))
    return pairs

# Function to find the maximum overlapping interval with the smallest price difference
def find_max_overlap_with_price(maximum_list, minimum_list):
    # Function to find the overlap between two intervals
    def overlap(interval1, interval2):
        start = max(interval1[0][0], interval2[0][0])
        end = min(interval1[0][1], interval2[0][1])
        if start < end and end-start > 86400*IS_length_min:  # Valid overlap
            return start, end
        return None  # No overlap

    max_overlap = 0
    min_price_difference = float('inf')
    best_result = None

    # Compare every interval in maximum_list with every interval in minimum_list
    for max_interval in maximum_list:
        for min_interval in minimum_list:
            overlapping_interval = overlap(max_interval, min_interval)
            if overlapping_interval:
                overlap_start, overlap_end = overlapping_interval
                overlap_duration = overlap_end - overlap_start

                # Interpolate prices for the overlapping start and end times
                def interpolate_price(interval, time):
                    price_start, price_end = interval[1][0], interval[1][1]
                    return price_start + (price_end - price_start) * ((time - interval[0][0]) / (interval[0][1] - interval[0][0]))

                max_price_start = interpolate_price(max_interval, overlap_start)
                max_price_end = interpolate_price(max_interval, overlap_end)
                min_price_start = interpolate_price(min_interval, overlap_start)
                min_price_end = interpolate_price(min_interval, overlap_end)

                # Calculate average price difference over the overlap
                price_difference = abs((max_price_start + max_price_end) / 2 - (min_price_start + min_price_end) / 2)

                # Update best interval if the overlap duration is larger or price difference is smaller
                if (overlap_duration > max_overlap) or (
                    overlap_duration == max_overlap and price_difference < min_price_difference):
                    max_overlap = overlap_duration
                    min_price_difference = price_difference
                    best_result = {
                        #"overlap_start": overlap_start,
                        #"overlap_end": overlap_end,
                        #"max_prices": (max_price_start, max_price_end),
                        #"min_prices": (min_price_start, min_price_end),
                        "max_int_start_time": max_interval[0][0],
                        "max_int_start_price": max_interval[1][0],
                        "max_int_end_time": max_interval[0][1],
                        "max_int_end_price": max_interval[1][1],
                        "min_int_start_time": min_interval[0][0],
                        "min_int_start_price": min_interval[1][0],
                        "min_int_end_time": min_interval[0][1],
                        "min_int_end_price": min_interval[1][1],
                    }
    return best_result

async def define_stability_interval(closes, high, low, times, volume,ctx):
        # Will be called at each candle.
    interval_stabilitate = False
    global sb
    global max_pairs
    global min_pairs
    local_maxim = [0]
    local_minim = [0]

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

    for i in range(medie_close_period,len(closes)-1):
        if closes[i-1] < closes[i] and closes[i] > closes[i+1]:
            if closes[i] / medie_close[i-medie_close_period] >= 1 + pr_vrf_dif_medie:
                local_maxim.append(closes[i])
            else:
                local_maxim.append(0)
        else:
            local_maxim.append(0)
    local_maxim.append(0) # to be removed !!! -------

    #Build the local_minim list
    for i in range(medie_close_period,len(closes)-1):
        if closes[i-1] > closes[i] and closes[i] < closes[i+1]:
            if closes[i] / medie_close[i-medie_close_period] <= 1 - pr_vrf_dif_medie:
                local_minim.append(closes[i])
            else:
                local_minim.append(0)
        else:
            local_minim.append(0)
    local_minim.append(0) # to be removed !!! -------

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

    max_pairs = await find_valid_pairs(local_maxim, times[:len(local_maxim)], proc_intre_vrf_line_IS, True)
    min_pairs = await find_valid_pairs(local_minim, times[:len(local_minim)], proc_intre_vrf_line_IS, False)

    best_result = find_max_overlap_with_price(max_pairs, min_pairs)

    return best_result


async def stability_interval():   
    global interval_stabil_final

    async def strategy(ctx):
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
            result = await define_stability_interval(closes[-interval_stabil:], high[-interval_stabil:], low[-interval_stabil:], times[-interval_stabil:], volume[-interval_stabil:],ctx)
            if result not in interval_stabil_final and result != None:
                interval_stabil_final.append(result)
        
        if times[-1] == times_global[-1] and len(interval_stabil_final)!=0:
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
    datafile = "ExchangeHistoryDataCollector_1725784408.359507.data"
     #data = await obs.get_data("ETH/USDT", "1d") #, start_timestamp=1720410417)
    data = await obs.get_data("ETH/USDT", "1d", data_file=datafile)

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
