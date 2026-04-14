# 因子处理模块

# 以后扩展因子较为简单
# 想加 RSI 因子？
# 新建 factors/rsi.py
# 写：
# python
# 运行
# def calculate(df, params):
#     df['rsi'] = talib.RSI(df['close'], 14)
#     return df
# 在 yaml 里加一行：
# yaml
# enabled_factors:
#   - rsi
# ✅ 不用改主代码！✅ 自动识别！✅ 自动计算！