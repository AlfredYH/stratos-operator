import akshare as ak
import tushare as ts
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
import yaml
import os


def key_config():
    CONFIG_PATH = "key.yaml"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_full_path = os.path.join(script_dir, CONFIG_PATH)

    with open(config_full_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            tushare_token = config["client"]["TUSHARE_TOKEN"]

    return tushare_token



# ===================== 1. 配置管理（极简版） =====================
class DataConfig():
    """数据采集配置类"""

    def __init__(self):
        self.config = {
            "data_source": "akshare",  # 可选：akshare/tushare
            "adjust_type": "",  # 复权方式：""(不复权)/qfq(前复权)/hfq(后复权)
            "tushare_token": key_config(),  # Tushare token（需自行申请）
            "debug_mode": False # 调试模式
        }

    def update_config(self, **kwargs):
        """动态更新配置"""
        for k, v in kwargs.items():
            if k in self.config:
                self.config[k] = v
            else:
                raise ValueError(f"不支持的配置项：{k}，可选：{list(self.config.keys())}")

    def get_config(self, key: str) -> Any:
        """获取配置值"""
        return self.config.get(key)


# ===================== 2. 核心数据采集类（完全对齐原始代码逻辑） =====================
class StockDataCollector():
    """股票数据采集器（修复AKShare核心逻辑）"""

    def __init__(self, config: Optional[DataConfig] = None):
        self.config = config or DataConfig()
        # 初始化Tushare（仅当使用tushare时）
        if self.config.get_config("data_source") == "tushare":
            token = self.config.get_config("tushare_token")
            if not token:
                raise ValueError("使用Tushare必须配置tushare_token！")
            ts.set_token(token)
            self.ts_pro = ts.pro_api()

    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        完全对齐原始代码的股票代码拼接逻辑
        输入：6位数字（如600970） → 输出：sh600970/sz300141
        """
        # 确保股票代码是字符串类型，补全6位
        if not isinstance(stock_code, str):
            stock_code = str(stock_code).zfill(6)

        # 完全复用原始代码的前缀逻辑
        if stock_code.startswith(('sz', 'sh')):
            return stock_code
        if stock_code.startswith(('0', '3')):
            return 'sz' + stock_code
        elif stock_code.startswith(('6', '9')):
            return 'sh' + stock_code
        else:
            raise ValueError(f"不支持的股票代码前缀：{stock_code[:1]}")

    def _format_akshare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """完全对齐原始代码的格式化逻辑"""
        if df.empty:
            return pd.DataFrame()

        # 原始代码的核心操作：新增date列→转datetime→设为索引
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # 仅保留指定字段（和原始代码一致）
        return df[['open', 'high', 'low', 'close', 'volume']]

    def _format_tushare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tushare数据格式化（对齐AKShare输出）"""
        if df.empty:
            return pd.DataFrame()

        # 日期处理（Tushare日期字段是trade_date）
        df['date'] = pd.to_datetime(df['trade_date'])
        df.set_index('date', inplace=True)

        # 成交量单位转换：手→股（×100）
        df['volume'] = df['vol'] * 100

        # 核心修改：按日期升序排序（从上到下从早到晚）
        df = df.sort_index(ascending=True)

        # 保留和AKShare一致的字段
        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_stock_data(self,
                       stock_code: str,
                       start_date: str,
                       end_date: str) -> Optional[pd.DataFrame]:
        """
        核心方法：完全对齐原始代码的AKShare调用逻辑
        """
        # 1. 复用原始代码的日期处理逻辑（仅转字符串，不修改格式）
        if not isinstance(start_date, str):
            start_date = str(start_date)
        if not isinstance(end_date, str):
            end_date = str(end_date)

        # 2. 股票代码标准化（完全对齐原始逻辑）
        try:
            normalized_code = self._normalize_stock_code(stock_code)
        except ValueError as e:
            print(f"❌ 股票代码处理失败：{e}")
            return None

        # 3. 调试信息（可选）
        if self.config.get_config("debug_mode"):
            print(
                f"🔍 调试信息：AKShare调用参数 → symbol={normalized_code}, start={start_date}, end={end_date}, adjust={self.config.get_config('adjust_type')}")

        # 4. 调用AKShare（完全复用原始代码的参数）
        data_source = self.config.get_config("data_source")
        adjust_type = self.config.get_config("adjust_type")

        try:
            if data_source == "akshare":
                # 完全对齐原始代码的akshare调用方式
                stock_hist_df = ak.stock_zh_a_daily(
                    symbol=normalized_code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust_type
                )
                df = self._format_akshare_data(stock_hist_df)

            elif data_source == "tushare":
                # Tushare调用逻辑（兼容原始输出格式）
                ts_code = f"{stock_code.zfill(6)}.SH" if stock_code.startswith(
                    ('6', '9')) else f"{stock_code.zfill(6)}.SZ"
                df_raw = self.ts_pro.daily(
                    ts_code=ts_code,
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adj=adjust_type if adjust_type else "none"
                )
                df = self._format_tushare_data(df_raw)

            else:
                print(f"❌ 不支持的数据源：{data_source}")
                return None

        except Exception as e:
            print(f"❌ {data_source}获取数据失败: {e}")
            return None

        if df.empty:
            print(f"⚠️  {data_source}未获取到{stock_code}在{start_date}-{end_date}的有效数据")
            return None
        if self.config.get_config("debug_mode"):
            print(f"✅ 成功获取{data_source}数据：{stock_code}（{start_date}至{end_date}），共{len(df)}条记录")
        return df


# ===================== 3. 测试代码（完全复现你的调用场景） =====================
if __name__ == "__main__":
    # 测试配置
    STOCK_CODE = '002110'
    START_DATE = '20251120'
    END_DATE = '20260315'

    # 初始化配置（完全对齐原始代码的参数）
    cfg = DataConfig()
    cfg.update_config(
        data_source="akshare",
        adjust_type="",  # 不复权（和原始代码一致）
        debug_mode=True
    )

    # 完全复用你的调用参数
    collector = StockDataCollector(cfg)
    result = collector.get_stock_data(STOCK_CODE, START_DATE, END_DATE)

    # 输出结果（和原始代码格式一致）
    if result is not None:
        print("\n=== 数据输出（前5行）===")
        print(result.head())
        print("\n=== 数据输出（后5行）===")
        print(result.tail())
        print(f"\n=== 数据维度 ===")
        print(f"行数：{len(result)}, 列数：{len(result.columns)}")
        print(f"列名：{list(result.columns)}")

    # 初始化配置（完全对齐原始代码的参数）
    cfg = DataConfig()
    cfg.update_config(
        data_source="tushare",
        adjust_type="",  # 不复权（和原始代码一致）
        tushare_token=key_config(),  # 从配置文件获取Tushare token
        debug_mode=True
    )

    # 完全复用你的调用参数
    collector2 = StockDataCollector(cfg)
    result = collector2.get_stock_data(STOCK_CODE, START_DATE, END_DATE)

    # 输出结果（和原始代码格式一致）
    if result is not None:
        print("\n=== 数据输出（前5行）===")
        print(result.head())
        print("\n=== 数据输出（后5行）===")
        print(result.tail())
        print(f"\n=== 数据维度 ===")
        print(f"行数：{len(result)}, 列数：{len(result.columns)}")
        print(f"列名：{list(result.columns)}")

    import utils.getdata_fromsqlite as getdata_fromsqlite
    print("\n=== 测试从SQLite获取数据 ===")
    df_sqlite = getdata_fromsqlite.get_stock_history(STOCK_CODE, START_DATE, END_DATE)
    if not df_sqlite.empty:
        print(f"✅ 成功从SQLite获取数据，共{len(df_sqlite)}条记录")
        print("=== 前5条数据预览（以日期为索引） ===")
        print(df_sqlite.head())
        print("=== 后5条数据预览（以日期为索引） ===")
        print(df_sqlite.tail())
        print("\n=== 索引类型 ===")
        print(f"索引类型：{type(df_sqlite.index)}")