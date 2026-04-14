import akshare as ak
import tushare as ts
import pandas as pd
from typing import Optional
from datetime import datetime

from .datacollect_config import get_config


class StockDataCollector(object):
    """
    股票数据采集器，支持从Akshare或Tushare获取股票历史K线数据
    """
    def __init__(self, data_source: str = "akshare", adjust_type: str = ""):
        self.data_source = data_source
        self.adjust_type = adjust_type
        self.debug_mode = get_config().debug_mode

        if data_source == "tushare":
            token = get_config().tushare_token
            if not token:
                raise ValueError("使用Tushare必须配置TUSHARE_TOKEN！")
            ts.set_token(token)
            self.ts_pro = ts.pro_api()

    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        标准化股票代码，添加交易所前缀
        
        Args:
            stock_code: 原始股票代码
        
        Returns:
            带前缀的股票代码，如 sz000001, sh600000
        """
        if not isinstance(stock_code, str):
            stock_code = str(stock_code).zfill(6)

        if stock_code.startswith(('sz', 'sh')):
            return stock_code
        if stock_code.startswith(('0', '3')):
            return 'sz' + stock_code
        elif stock_code.startswith(('6', '9')):
            return 'sh' + stock_code
        else:
            raise ValueError(f"不支持的股票代码前缀：{stock_code[:1]}")

    def _format_akshare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化Akshare返回的数据"""
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def _format_tushare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化Tushare返回的数据"""
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['trade_date'])
        df.set_index('date', inplace=True)
        df['volume'] = df['vol'] * 100
        df = df.sort_index(ascending=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            包含K线数据的DataFrame，失败返回None
        """
        if not isinstance(start_date, str):
            start_date = str(start_date)
        if not isinstance(end_date, str):
            end_date = str(end_date)

        try:
            normalized_code = self._normalize_stock_code(stock_code)
        except ValueError as e:
            print(f"❌ 股票代码处理失败：{e}")
            return None

        if self.debug_mode:
            print(f"🔍 调试信息：{self.data_source}调用参数 → symbol={normalized_code}, start={start_date}, end={end_date}, adjust={self.adjust_type}")

        try:
            if self.data_source == "akshare":
                stock_hist_df = ak.stock_zh_a_daily(
                    symbol=normalized_code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=self.adjust_type
                )
                df = self._format_akshare_data(stock_hist_df)

            elif self.data_source == "tushare":
                ts_code = f"{stock_code.zfill(6)}.SH" if stock_code.startswith(('6', '9')) else f"{stock_code.zfill(6)}.SZ"
                df_raw = self.ts_pro.daily(
                    ts_code=ts_code,
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adj=self.adjust_type if self.adjust_type else "none"
                )
                df = self._format_tushare_data(df_raw)

            else:
                print(f"❌ 不支持的数据源：{self.data_source}")
                return None

        except Exception as e:
            print(f"❌ {self.data_source}获取数据失败: {e}")
            return None

        if df.empty:
            print(f"⚠️  {self.data_source}未获取到{stock_code}在{start_date}-{end_date}的有效数据")
            return None
        if self.debug_mode:
            print(f"✅ 成功获取{self.data_source}数据：{stock_code}（{start_date}至{end_date}），共{len(df)}条记录")
        return df


def get_stock_data(stock_code: str, start_date: str, end_date: str, 
                   data_source: str = "akshare", adjust_type: str = "") -> Optional[pd.DataFrame]:
    collector = StockDataCollector(data_source, adjust_type)
    return collector.get_stock_data(stock_code, start_date, end_date)