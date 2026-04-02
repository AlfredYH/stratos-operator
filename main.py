from trader.trader import TradeOperator

if __name__ == "__main__":
    operator = TradeOperator()
    # operator.get_position_info()
    # print("持仓信息已获取")
    print(operator.get_trade_info())