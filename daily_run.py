
from utils.daily_update import DailyUpdate
import os
import re
import akshare as ak
import datetime
import pandas as pd



if __name__ == "__main__":

    today = datetime.date.today()
    # 获取A股交易日历
    trade_cal_df = ak.tool_trade_date_hist_sina()
    # 转为日期格式
    trade_cal_df["trade_date"] = pd.to_datetime(trade_cal_df["trade_date"]).dt.date
    # 判断今天是否是交易日
    if today in trade_cal_df["trade_date"].values:
        print(f"✅ {today} 是交易日，开始同步数据...")
        dataupdate = DailyUpdate()
        # dataupdate.get_all_stock_list() # 获取股票列表并保存到CSV文件
        dataupdate.run_sync_process(adjust_type="bfq", debug_mode=True) # 同步不复权数据（bfq）
        dataupdate.run_sync_process(adjust_type="qfq", debug_mode=True) # 同步前复权数据（qfq）

    else:
        print(f"❌ {today} 不是交易日，跳过数据同步。")
        exit(0)
    



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

