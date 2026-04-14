import numpy as np
import talib

def calculate(df, params):
    close = np.asarray(df["close"], dtype=np.float64)
    upper, mid, lower = talib.BBANDS(
        close,
        timeperiod=params["bb_period"],
        nbdevup=params["bb_dev"],
        nbdevdn=params["bb_dev"]
    )
    df["bb_upper"] = upper
    df["bb_lower"] = lower
    df["bb_width"] = upper - lower
    df["bb_div"] = (upper - lower) / (mid + 1e-9)
    df["bb_width_slope"] = talib.LINEARREG_SLOPE(df["bb_width"].astype(np.float64), 4)
    df["bb_close_div"] = (2 * close - (close + lower)) / (upper - lower + 1e-9)
    return df