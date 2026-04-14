import numpy as np

def calculate(df, params):
    v_log = np.log(df["volume"] + 1)
    df["volume_log"] = v_log

    v_ma = v_log.rolling(params["volume_z_period"]).mean()
    v_std = v_log.rolling(params["volume_z_period"]).std()
    df["volume_z"] = (v_log - v_ma) / (v_std + 1e-9)
    return df