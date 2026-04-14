def calculate(df, params):
    df = df.copy()
    df["target"] = df["close"].shift(-params["target_forward_days"]) / df["close"] - 1
    return df