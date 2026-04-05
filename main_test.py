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








    #################################################################
    # 每日删除当前文件夹下的 libhv.数字.log 文件，防止日志文件过多占用空间
    #################################################################


    # 匹配规则：libhv + 点 + 纯数字 + 点 + log
    pattern = re.compile(r"^libhv\.\d+\.log$")

    # 遍历当前文件夹
    for filename in os.listdir("."):
        if pattern.match(filename):
            try:
                os.remove(filename)
                print(f"✅ 已删除: {filename}")
            except Exception as e:
                print(f"❌ 删除失败 {filename}: {e}")

