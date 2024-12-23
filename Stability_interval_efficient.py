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
closes = []
# times = []
# volume = []
# high = []
# low = []

medie_close = []
medie_volum = []
interval_stabil_flag = False
interval_stabil_print = []
initial = True
interval_stabil_final=[]
counter_strategy_run=0
counter_strategy_run = 0


IS_length_min = 45  # nr pozitii minime intre varfuri
IS_procent_max = 0.20 # 0.15 -> 15% procent intre max si minim in interval stabil
proc_intre_vrf_line_IS = 0.03  # (3% procent intre vf-uri de max sau min)
interval_stabil = 150

procent_spargere_IS = 0.05  #(5%)

procent_volum_max = 0.3 # (80%)  # volume mari pe buy [only]
procent_high_close_cross = 0.3 # (20% diferenta intre ele)
var_nr_volume = 3  #cate volume mari sa fie in IS
medie_close_period = 7

#--------------------------FUNCTIONS------------------------------

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


def analyze_the_break(last_closes, last_high, last_low, last_times, interval_stabil_local):
    # Check if closes breaks the stability interval
    if last_closes > interval_stabil_local["price_max"]:
        # check if the high/close ratio is good ( no more than procent_high_close_cross % )
        if ( last_closes - last_low ) / ( last_high - last_low ) > 1 - procent_high_close_cross:
            print("spargere buna la: ", datetime.fromtimestamp(last_times).strftime('%Y-%m-%d'), "cu pret: ", last_closes, " pentru maxim_la_interval de: ", interval_stabil_local["price_max"])
            return True
        else:
            print("spargere rea in sus la: ", datetime.fromtimestamp(last_times).strftime('%Y-%m-%d'), "cu pret: ", last_closes, " pentru maxim_la_interval de: ", interval_stabil_local["price_max"])
            return False
    else:
        # check if it breaks the lower interval
        if last_closes < interval_stabil_local["price_min"]:
            print("spargere in jos la: ", datetime.fromtimestamp(last_times).strftime('%Y-%m-%d'), "cu pret: ", last_closes, " pentru minim_la_interval de: ", interval_stabil_local["price_min"])
            return False
        else:
            return None

    
def merge_stability_intervals(check_interval):
    if not check_interval:
        return []
    else:
        if len(check_interval)==1:
            return check_interval[0]

    # Sort intervals by start_time
    sorted_intervals = sorted(check_interval, key=lambda x: x['start_time'])
    merged_intervals = []

    # Initialize the first interval
    current_interval = sorted_intervals[0]

    for next_interval in sorted_intervals[1:]:
        # Check for overlap or contiguity
        if next_interval['start_time'] <= current_interval['end_time']:
            # Merge intervals by extending the end_time and adjusting prices
            current_interval['end_time'] = max(current_interval['end_time'], next_interval['end_time'])
            current_interval['human_end_time'] = datetime.fromtimestamp(current_interval['end_time']).strftime('%Y-%m-%d')
            current_interval['price_end'] = next_interval['price_end']
            current_interval['price_max'] = max(current_interval['price_max'], next_interval['price_max'])
            current_interval['price_min'] = min(current_interval['price_min'], next_interval['price_min'])
        else:
            # No overlap, add the current interval to the result and move to the next
            merged_intervals.append(current_interval)
            current_interval = next_interval

    # Add the last interval
    merged_intervals.append(current_interval)

    return merged_intervals

async def find_stability_intervals(closes, IS_length_min, IS_procent_max, times):
    check_interval = []
    stable_interval = []
    for start in range(1,len(closes) - IS_length_min + 1):
        window_prices = closes[start:start + IS_length_min]
        pct_change = (max(window_prices) - min(window_prices)) / min(window_prices)
        if pct_change <= IS_procent_max:
            result = {
                        "start_time": times[start-1],
                        "human_start_time": datetime.fromtimestamp(times[start-1]).strftime('%Y-%m-%d'),
                        "price_start": closes[start],
                        "end_time": times[start + IS_length_min - 2],
                        "human_end_time": datetime.fromtimestamp(times[start + IS_length_min - 2]).strftime('%Y-%m-%d'),
                        "price_end": closes[start + IS_length_min - 1],
                        "price_max": max(window_prices),
                        "price_min": min(window_prices),
                    }
            if result["start_time"] > result["end_time"]:
                print("stop!")
            check_interval.append(result)

    if len(check_interval) > 1:
        stable_interval = merge_stability_intervals(check_interval)
        if len(stable_interval) > 1:
            for each_interval in stable_interval:
                if each_interval["end_time"]==times[-2]:
                    stable_interval= each_interval
                else:
                    stable_interval= None

        else:
            if stable_interval[0]["end_time"]==times[-2]:
                stable_interval= stable_interval[0]
            else:
                stable_interval= None

    else:
        if check_interval:
            if check_interval[0]["end_time"]==times[-2]:
                stable_interval= check_interval[0]
            else:
                stable_interval= None
        else:
            stable_interval=None
        
    #check if stable_interval is a good interval:
    stable_interval = await finalize_stability_interval(stable_interval,closes,times)

    return stable_interval

async def finalize_stability_interval(check_interval,closes,times):
    # initial build of local_maxim, local_minim and check if there is already a stable interval

    if check_interval == None:
        return None

    global high
    global low
    global medie_close
    local_maxim = []
    local_minim = []
    the_maxim = []
    the_minim = []

    # for i in range(medie_close_period):
    #     local_maxim.append(0)
    #     local_minim.append(0)
    
    index_price_start=0
    index_price_end=0

    #find the index for the price_start and price end in closes -> in order to find the max and min
    for i,each in enumerate(closes):
        if each == check_interval["price_start"] and check_interval["start_time"]==times[i-1]:
            index_price_start = i
        if each == check_interval["price_end"] and check_interval["end_time"]==times[i-1]:
            index_price_end = i

    if index_price_start == 0 or index_price_end == 0:
        #something is wrong !
        return None

    for i in range(index_price_start,index_price_end):
        
        #build local maxim_list
        if closes[i-1] < closes[i] and closes[i] > closes[i+1]:
            #if closes[i] / medie_close[i-medie_close_period] >= 1 + pr_vrf_dif_medie:
            local_maxim.append(closes[i])
        
        #build local minim list
        if closes[i-1] > closes[i] and closes[i] < closes[i+1]:
            #if closes[i] / medie_close[i-medie_close_period] <= 1 - pr_vrf_dif_medie:
            local_minim.append(closes[i])

    no_highs = 0
    for each in local_maxim:
        if each == 0:
            continue
        else:
            #if the maximums are higher than price_max* proc_intre_vrf_line_IS*100 (%) [90%] then is a good high
            if each >= check_interval["price_max"]*(1-proc_intre_vrf_line_IS):
                the_maxim.append(each)
                no_highs+=1
    
    no_lows = 0
    for each in local_minim:
        if each == 0:
            continue
        else: 
            #if the minimums are at lower than price_min proc_intre_vrf_line_IS*100 (%) [90%] then is a good low
            if each <= check_interval["price_min"]*(1+proc_intre_vrf_line_IS):
                the_minim.append(each)
                no_lows+=1
    
    #there should be minimum 2 Highs and 2 Lows
    if no_highs>1 and no_lows>=1:
        best_result = check_interval
        print("GoodInterval:", best_result)
    else:
        return None

    # await obs.plot(ctx, "Medie_close", times[:], medie_close, mode="lines",color="blue")
    # await obs.plot(ctx, "Local_maxim", times[:], local_maxim, mode="lines",color="white")
    # await obs.plot(ctx, "Local_minim", times[:], local_minim, mode="lines",color="green")

    return best_result


async def money_maker(symbol,start_time,end_time):

    async def strategy(ctx):
        global initial
        global interval_stabil_final
        global interval_stabil_flag
        global interval_stabil_print

        if run_data["entries"] is None:
            # Compute entries only once per backtest.
            times_global = await obs.Time(ctx, max_history=True, use_close_time=True)
        
        closes = await obs.Close(ctx)
        high = await obs.High(ctx)
        low = await obs.Low(ctx)
        times = await obs.Time(ctx, use_close_time=True)
        volume = await obs.Volume(ctx)

        if len(closes) < int(interval_stabil/2):
            return
        else:
            if interval_stabil_flag == False: 
                result1 = await find_stability_intervals(closes[-interval_stabil:], IS_length_min, IS_procent_max, times[-interval_stabil:])
                if result1:
                    interval_stabil_flag=True
                    interval_stabil_final=result1
            else:
                mod = analyze_the_break(closes[-1], high[-1], low[-1], times[-2], interval_stabil_final)
                if mod == True:
                    interval_stabil_flag=False
                    interval_stabil_print.append(interval_stabil_final)
                    await obs.market(ctx, "buy", amount="10%", stop_loss_offset="-20%", take_profit_offset="35%")
                else:
                    if mod == False:
                        interval_stabil_flag=False
                    else:
                        #we are still in stability interval
                        interval_stabil_final["end_time"]= times[-2]
                        interval_stabil_final["human_end_time"]= datetime.fromtimestamp(times[-2]).strftime('%Y-%m-%d')
                        interval_stabil_final["price_end"]= closes[-1]
                        interval_stabil_flag=True


        
        if times[-1] == times_global[-1] and len(interval_stabil_final)!=0:
            #After all intervals were found - find overlapping intervals and choose the longest
            # with the lowest price diff
            
            #preparing stability intervals found for plotting
            for counter,interval in enumerate(interval_stabil_print):
                """
                Building the stability period intervals:
                -> Find index of the start interval in times_global rage
                -> start filling with 0 until start of the interval, then maximum of the values of the staiblity interval until end time
                -> then 0 until lenght of times_global
                """
                printable_interval_max = []
                printable_interval_min = []
                index_start = times_global.index(interval["start_time"])
                index_end = times_global.index(interval["end_time"])
                
                if index_start and index_end:
                    #start filling printable_interval_max with 0 until max_interval found
                    for i in range(index_start):
                        printable_interval_max.append(0)
                    #start filling printable_interval_min with 0 until min_interval found
                        printable_interval_min.append(0)
                    
                    for i in range(index_end-index_start):
                        printable_interval_max.append(interval["price_max"])
                        printable_interval_min.append(interval["price_min"])
                    
                    for i in range(len(times_global)-index_end):
                        printable_interval_max.append(0)
                        printable_interval_min.append(0)
                else:
                    print("One of the time intervals was not found for printing!")

                await obs.plot(ctx, "Interval_max"+str(counter), times_global[:], printable_interval_max, mode="scatter",color="green", chart="main-chart")
                await obs.plot(ctx, "Interval_min"+str(counter), times_global[:], printable_interval_min, mode="scatter",color="red", chart="main-chart")


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
    #datafile = "ExchangeHistoryDataCollector_1734368220.1443067.data"
    data = await obs.get_data(symbol, "1d", start_timestamp=start_time, end_timestamp=end_time)
    #data = await obs.get_data(symbol, "1d", start_timestamp=start_time, end_timestamp=end_time)
    
    #print(f"Data read started at: {time.strftime('%X')}")
    #data = await obs.get_data(symbol, "1d", data_file=datafile)
    #print(f"Data read end at: {time.strftime('%X')}")

    run_data = {
        "entries": None,
    }
     # Run a backtest using the above data, strategy and configuration.
    
    #print(f"Strategy run started at: {time.strftime('%X')}")
    res = await obs.run(data, strategy, config)
    
    #print("Stability Intervals found: ", interval_stabil_final)


    print(res.describe())
     # Generate and open report including indicators plots
    await res.plot(show=True)
     # Stop data to release local databases.
    await data.stop()


 # Call the execution of the script inside "asyncio.run" as
 # OctoBot-Script runs using the python asyncio framework.

start_time_human = "2023-06-01"
end_time_human = "2024-12-16"

dt_object = datetime.strptime(start_time_human, "%Y-%m-%d")
epoch_time_start = int(time.mktime(dt_object.timetuple()))
dt_object = datetime.strptime(end_time_human, "%Y-%m-%d")
epoch_time_end = int(time.mktime(dt_object.timetuple()))

symbol_list = {
    #"ETH/USDT",
    #"BTC/USDT",
    #"XRP/USDT",
    #"DAR/USDT",
    #"TWT/USDT",
    "CTXC/USDT",
    #"THETA/USDT",
}

for each in symbol_list:
    result = asyncio.run(money_maker(each,epoch_time_start,epoch_time_end))
    interval_stabil_print = []
    interval_stabil_final = []

print("done!")
