from trader.trader import TradeOperator
from utils.daily_update import DailyUpdate
import os
import re



if __name__ == "__main__":
    # operator = TradeOperator()
    
    # operator.get_position_info()
    # print(operator.get_position_info())

    # operator.buy_in(stock_code="002110", quantity=100)
    dataupdate = DailyUpdate()
    # dataupdate.get_all_stock_list() # 获取股票列表并保存到CSV文件
    dataupdate.run_sync_process(adjust_type="bfq", debug_mode=True) # 同步不复权数据（bfq）








