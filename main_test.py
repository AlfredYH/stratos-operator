from trader.trader import TradeOperator

if __name__ == "__main__":
    operator = TradeOperator()
    
    # operator.get_position_info()
    # print(operator.get_position_info())

    operator.buy_in(stock_code="002110", quantity=100)

