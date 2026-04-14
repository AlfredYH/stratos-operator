import numpy as np
import talib

def calculate(df, params):
    close = np.asarray(df["close"], dtype=np.float64)
    macd, sig, hist = talib.MACD(
        close,
        fastperiod=params["macd_fast"],
        slowperiod=params["macd_slow"],
        signalperiod=params["macd_signal"]
    )
    df["macd"] = macd
    df["macd_signal"] = sig
    df["macd_hist"] = hist
    df["macd_slope"] = talib.LINEARREG_SLOPE(macd, timeperiod=3)
    return df