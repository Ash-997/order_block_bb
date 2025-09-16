from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class OrderBlock:
    def __init__(self, top, btm, loc, breaker=False, break_loc=None):
        self.top = top
        self.btm = btm
        self.loc = loc
        self.breaker = breaker
        self.break_loc = break_loc


def detect_order_blocks(df, length=10, showBull=3, showBear=3, useBody=False):
    """
    Detect LuxAlgo style Order Blocks & Breaker Blocks

    Args:
        df (pd.DataFrame): must have columns ['open','high','low','close']
        length (int): swing lookback
        showBull (int): max bullish OBs to keep
        showBear (int): max bearish OBs to keep
        useBody (bool): if True, use candle bodies else wicks

    Returns:
        bullish_obs, bearish_obs : lists of dict with OB data
    """

    bullish_obs = []
    bearish_obs = []

    # choose wick or body for calculations
    df["max"] = df[["close", "open"]].max(axis=1) if useBody else df["high"]
    df["min"] = df[["close", "open"]].min(axis=1) if useBody else df["low"]

    # stateful variables for swing detection
    os = 0
    top = {'y': np.nan, 'x': 0, 'crossed': False}
    btm = {'y': np.nan, 'x': 0, 'crossed': False}

    for n in range(length, len(df)):
        row = df.iloc[n]

        # === Swing Detection (from Pine Script) ===
        upper = df['high'].iloc[n-length+1 : n+1].max()
        lower = df['low'].iloc[n-length+1 : n+1].min()
        high_len_ago = df['high'].iloc[n-length]
        low_len_ago = df['low'].iloc[n-length]

        prev_os = os
        if high_len_ago > upper:
            os = 0
        elif low_len_ago < lower:
            os = 1

        if os == 0 and prev_os != 0:
            top = {'y': df['high'].iloc[n - length], 'x': n - length, 'crossed': False}

        if os == 1 and prev_os != 1:
            btm = {'y': df['low'].iloc[n - length], 'x': n - length, 'crossed': False}

        # === Bullish OB detection (using stateful swings) ===
        if not np.isnan(top['y']) and not top['crossed'] and row["close"] > top['y']:
            top['crossed'] = True # prevent re-triggering on the same swing

            minima = df['min'].iloc[n - 1]
            maxima = df['max'].iloc[n - 1]
            loc = df.index[n - 1]

            # Variable-length backward search
            for i in range(1, (n - top['x'])):
                idx = n - i

                prev_minima = minima
                minima = min(minima, df["min"].iloc[idx])
                if minima != prev_minima:
                    maxima = df["max"].iloc[idx]
                    loc = df.index[idx]

            bullish_obs.insert(0, OrderBlock(maxima, minima, loc))

        # Update bullish OBs
        for i in range(len(bullish_obs) - 1, -1, -1):
            ob = bullish_obs[i]
            if not ob.breaker:
                if min(row["close"], row["open"]) < ob.btm:
                    ob.breaker = True
                    ob.break_loc = df.index[n]
            else:
                if row["close"] > ob.top:
                    bullish_obs.pop(i)

        # === Bearish OB detection (using stateful swings) ===
        if not np.isnan(btm['y']) and not btm['crossed'] and row["close"] < btm['y']:
            btm['crossed'] = True # prevent re-triggering

            minima = df['min'].iloc[n - 1]
            maxima = df['max'].iloc[n - 1]
            loc = df.index[n - 1]

            # Variable-length backward search
            for i in range(1, (n - btm['x'])):
                idx = n - i

                prev_maxima = maxima
                maxima = max(maxima, df["max"].iloc[idx])
                if maxima != prev_maxima:
                    minima = df["min"].iloc[idx]
                    loc = df.index[idx]

            bearish_obs.insert(0, OrderBlock(maxima, minima, loc))

        # Update bearish OBs
        for i in range(len(bearish_obs) - 1, -1, -1):
            ob = bearish_obs[i]
            if not ob.breaker:
                if max(row["close"], row["open"]) > ob.top:
                    ob.breaker = True
                    ob.break_loc = df.index[n]
            else:
                if row["close"] < ob.btm:
                    bearish_obs.pop(i)

    # Limit shown OBs
    bullish_obs = bullish_obs[:showBull]
    bearish_obs = bearish_obs[:showBear]

    # return as dicts for easy use
    bull_dicts = [vars(ob) for ob in bullish_obs]
    bear_dicts = [vars(ob) for ob in bearish_obs]

    return bull_dicts, bear_dicts


# ================================
# Example run
# ================================
if __name__ == "__main__":
    tv = TvDatafeed()
    df = tv.get_hist(
        symbol="NIFTY", exchange="NSE",
        interval=Interval.in_5_minute, n_bars=1000
    )
    df.to_csv('zzzz.csv')
    bull, bear = detect_order_blocks(df, length=10, showBull=15, showBear=1, useBody=False)

    # print("Bullish OBs:", bull)
    for b in bull:
        print(b)

    # print("Bearish OBs:", bear)

    # ============ OPTIONAL PLOT ============
    plt.figure(figsize=(14, 6))
    plt.plot(df.index, df["close"], label="Close Price", color="black")

    # Plot bullish OBs
    for ob in bull:
        plt.axhspan(ob["btm"], ob["top"], color="green", alpha=0.3)
        plt.axvline(ob["loc"], color="green", linestyle="--")

    # Plot bearish OBs
    for ob in bear:
        plt.axhspan(ob["btm"], ob["top"], color="red", alpha=0.3)
        plt.axvline(ob["loc"], color="red", linestyle="--")

    plt.legend()
    plt.title("Order Blocks Detection (LuxAlgo style)")
    plt.show()
