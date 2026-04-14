import numpy as np
import talib

def calculate(df, params):
    close = np.asarray(df["close"], dtype=np.float64)

    # 从配置读取周期
    ma_short = talib.MA(close, timeperiod=params["ma_short"])
    ma_mid   = talib.MA(close, timeperiod=params["ma_mid"])
    ma_long  = talib.MA(close, timeperiod=params["ma_long"])

    # 统一用配置KEY命名，不写死数字！
    df["ma_short_bias"]    = (close / ma_short) - 1
    df["ma_mid_bias"]      = (close / ma_mid) - 1
    df["ma_long_bias"]     = (close / ma_long) - 1

    df["ma_short_over_mid"] = (ma_short / ma_mid) - 1

    return df