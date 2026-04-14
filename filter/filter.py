import os
import yaml
import pandas as pd
import tushare as ts
import akshare as ak
import datetime



# ======================== 路径配置 ========================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KEY_PATH = os.path.join(ROOT, "utils", "key.yaml")
STOCK_POOL_PATH = os.path.join(ROOT, "utils", "stock_pool.parquet")
CONFIG_PATH = os.path.join(ROOT, "filter", "filter.yaml")
# 筛选过后的股票就从filter文件夹里读取，防止后续改动导致股票池丢失
# STOCK_POOL_PATH = os.path.join(ROOT, "filter", "stock_pool.parquet")



class StockFilter():
    def __init__(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        with open(KEY_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            tushare_token = config["client"]["TUSHARE_TOKEN"]

        ts.set_token(tushare_token)
        self.pro = ts.pro_api()

        today = datetime.date.today()
        # 获取A股交易日历
        trade_cal_df = ak.tool_trade_date_hist_sina()
        # 转为日期格式
        trade_cal_df["trade_date"] = pd.to_datetime(trade_cal_df["trade_date"]).dt.date
        # 判断今天是否是交易日
        if today in trade_cal_df["trade_date"].values:
            trading_date = today.strftime("%Y%m%d")

        else:
            trading_date = trade_cal_df[trade_cal_df["trade_date"] < today]["trade_date"].max().strftime("%Y%m%d")

        self.trading_date = trading_date






    def _abandon_st_stocks(self):
        """获取当前日期的ST股票列表"""
        df = self.pro.stock_st(self.trading_date)

        

        return df["ts_code"].tolist()
    


    def filt_by_pe(self, trade_date: str):
        # 市盈率筛选

    def filt_by_pb(self, trade_date: str):
        # 市净率筛选