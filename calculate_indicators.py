from tvDatafeed import TvDatafeed, Interval
import pandas as pd

tv = TvDatafeed()

df = tv.get_hist(symbol="NIFTY", exchange='NSE', interval=Interval.in_5_minute, n_bars=4000)

def find_swing_highs_lows(df, n=2):
    """
    Find swing highs and lows in the dataframe.
    n: number of candles on each side to check.
    """
    df['swing_high'] = df['high'].rolling(window=2*n+1, center=True).apply(lambda x: x[n] == max(x), raw=True)
    df['swing_low'] = df['low'].rolling(window=2*n+1, center=True).apply(lambda x: x[n] == min(x), raw=True)
    return df

def is_bullish_candle(df):
    return df['close'] > df['open']

def is_bearish_candle(df):
    return df['close'] < df['open']

def find_order_blocks(df):
    swing_highs = df[df['swing_high'] == 1]
    swing_lows = df[df['swing_low'] == 1]

    order_blocks = []

    for low_index, low_row in swing_lows.iterrows():
        # Find the candles between this swing low and the previous swing high
        prev_highs = swing_highs[swing_highs.index < low_index]
        if not prev_highs.empty:
            prev_high = prev_highs.iloc[-1]
            move_df = df[(df.index >= prev_high.name) & (df.index <= low_index)]

            # The bullish order block is the last bearish candle in this range
            bearish_candles = move_df[is_bearish_candle(move_df)]
            if not bearish_candles.empty:
                bullish_ob = bearish_candles.iloc[-1]
                order_blocks.append({'type': 'bullish', 'start': bullish_ob.name, 'end': bullish_ob.name, 'top': bullish_ob['high'], 'bottom': bullish_ob['low']})

    for high_index, high_row in swing_highs.iterrows():
        # Find the candles between this swing high and the previous swing low
        prev_lows = swing_lows[swing_lows.index < high_index]
        if not prev_lows.empty:
            prev_low = prev_lows.iloc[-1]
            move_df = df[(df.index >= prev_low.name) & (df.index <= high_index)]

            # The bearish order block is the last bullish candle in this range
            bullish_candles = move_df[is_bullish_candle(move_df)]
            if not bullish_candles.empty:
                bearish_ob = bullish_candles.iloc[-1]
                order_blocks.append({'type': 'bearish', 'start': bearish_ob.name, 'end': bearish_ob.name, 'top': bearish_ob['high'], 'bottom': bearish_ob['low']})

    return order_blocks

def find_breaker_blocks(df, order_blocks):
    breaker_blocks = []
    for ob in order_blocks:
        if ob['type'] == 'bullish':
            # Check if price closes below the low of the bullish OB
            break_df = df[df.index > ob['end']]
            break_point = break_df[break_df['close'] < ob['bottom']]
            if not break_point.empty:
                breaker_blocks.append({'type': 'bearish_breaker', 'start': ob['start'], 'end': break_point.index[0], 'top': ob['top'], 'bottom': ob['bottom']})
        elif ob['type'] == 'bearish':
            # Check if price closes above the high of the bearish OB
            break_df = df[df.index > ob['end']]
            break_point = break_df[break_df['close'] > ob['top']]
            if not break_point.empty:
                breaker_blocks.append({'type': 'bullish_breaker', 'start': ob['start'], 'end': break_point.index[0], 'top': ob['top'], 'bottom': ob['bottom']})
    return breaker_blocks


# Find swing points
df = find_swing_highs_lows(df)

# Find order blocks
order_blocks = find_order_blocks(df)

# Find breaker blocks
breaker_blocks = find_breaker_blocks(df, order_blocks)

# Add the order blocks and breaker blocks to the main dataframe
df['order_block'] = None
df['breaker_block'] = None

for ob in order_blocks:
    df.loc[ob['start'], 'order_block'] = f"{ob['type']} OB"

for bb in breaker_blocks:
    df.loc[bb['start'], 'breaker_block'] = f"{bb['type']}"

# Save the dataframe to an excel file
df.to_excel('nifty_data.xlsx')

print("Excel file 'nifty_data.xlsx' created successfully.")
