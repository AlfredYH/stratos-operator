def calculate(df, params):
    df = df.copy()
    df["price_dif_max"] = df["high"] - df["low"]
    df["price_dif"] = df["close"] - df["open"]
    return df