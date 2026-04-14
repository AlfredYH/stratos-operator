import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import akshare as ak

from .datacollect_config import get_config
from .data_collect import StockDataCollector


class DatabaseManager(object):
    """
    数据库管理器，负责SQLite数据库的连接、表创建、数据插入等操作
    """
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self):
        """连接数据库并优化性能参数"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, self.db_name)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._optimize()

    def _optimize(self):
        """优化SQLite数据库性能"""
        self.cursor.execute("PRAGMA synchronous = OFF")
        self.cursor.execute("PRAGMA journal_mode = WAL")
        self.cursor.execute("PRAGMA cache_size = -100000")

    def create_table(self, table_name: str):
        """创建股票数据表及索引"""
        self.cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            trade_date DATE, stock_code TEXT, stock_name TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        );""")
        self.cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_cd ON {table_name}(stock_code, trade_date);")
        self.conn.commit()

    def get_last_dates(self, table_name: str) -> dict:
        """获取每只股票的最新交易日期"""
        try:
            self.cursor.execute(f"SELECT stock_code, MAX(trade_date) FROM {table_name} GROUP BY stock_code")
            return {code: dt for code, dt in self.cursor.fetchall()}
        except:
            return {}

    def insert_batch(self, df: pd.DataFrame, table_name: str, stock_code: str, stock_name: str):
        """
        批量插入股票数据
        
        Args:
            df: 股票数据DataFrame
            table_name: 表名
            stock_code: 股票代码
            stock_name: 股票名称
        """
        try:
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["stock_code"] = stock_code
            df["stock_name"] = stock_name
            df.rename(columns={"date": "trade_date"}, inplace=True)
            df.to_sql(table_name, self.conn, if_exists="append", index=False)
            return True
        except:
            return False

    def commit(self):
        """提交事务"""
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class StockListProvider(object):
    """
    股票列表提供者，负责从Akshare或Tushare获取股票列表
    """
    def __init__(self, list_name: str):
        self.list_name = list_name

    @property
    def file_path(self):
        """获取股票列表文件路径"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, self.list_name)

    def load(self) -> Optional[pd.DataFrame]:
        """从本地Parquet文件加载股票列表"""
        try:
            return pd.read_parquet(self.file_path)
        except:
            return None

    def save(self, df: pd.DataFrame):
        """保存股票列表到Parquet文件"""
        df.to_parquet(self.file_path, index=False, engine="pyarrow")

    def fetch_from_akshare(self) -> Optional[pd.DataFrame]:
        """从Akshare获取股票列表"""
        try:
            stock_df = ak.stock_info_a_code_name()
            stock_df["代码"] = stock_df["代码"].astype(str).str.zfill(6)
            stock_df.rename(columns={"代码": "stock_code", "名称": "stock_name"}, inplace=True)
            stock_df = stock_df.astype({"stock_code": "string", "stock_name": "string"})
            self.save(stock_df)
            print("✅ 成功保存股票列表到 Parquet")
            return stock_df
        except Exception as e:
            print(f"⚠️ Akshare 失败: {e}")
            return None

    def fetch_from_tushare(self) -> Optional[pd.DataFrame]:
        """从Tushare获取股票列表"""
        try:
            import tushare as ts
            token = get_config().tushare_token
            ts.set_token(token)
            stock_df = ts.pro_api().stock_basic(exchange='', list_status='L', fields='symbol,name')
            stock_df.rename(columns={"symbol": "stock_code", "name": "stock_name"}, inplace=True)
            stock_df["stock_code"] = stock_df["stock_code"].astype(str).str.zfill(6)
            stock_df = stock_df.astype({"stock_code": "string", "stock_name": "string"})
            self.save(stock_df)
            print("✅ Tushare 保存成功 (Parquet)")
            return stock_df
        except Exception as e:
            print(f"❌ Tushare 失败: {e}")
            return None

    def get_stock_list(self):
        """获取股票列表，优先从本地加载，失败则从网络获取"""
        df = self.load()
        if df is not None and not df.empty:
            return df
        df = self.fetch_from_akshare()
        if df is None or df.empty:
            df = self.fetch_from_tushare()
        return df


class DailyUpdate(object):
    """
    每日数据更新主类，负责协调股票列表获取和数据同步
    """
    def __init__(self):
        cfg = get_config()
        self.db_manager = DatabaseManager(cfg.db_name)
        self.stock_list_provider = StockListProvider(cfg.list_name)
        self.max_workers = cfg.max_workers
        self.batch_commit = cfg.batch_commit
        self.target_date = date.today().strftime("%Y-%m-%d")

    TABLE_MAP = {
        "bfq": "daily_price_bfq",
        "qfq": "daily_price_qfq",
        "hfq": "daily_price_hfq"
    }

    def run_sync_process(self, adjust_type: str = "bfq", data_source: str = "akshare", debug_mode: bool = False):
        """
        运行同步进程，获取并更新股票历史数据
        
        Args:
            adjust_type: 复权类型，可选 bfq/qfq/hfq
            data_source: 数据源，可选 akshare/tushare
            debug_mode: 是否打印调试信息
        """
        allowed = ("qfq", "hfq", "bfq")
        if adjust_type not in allowed:
            raise ValueError(f"adjust_type 必须是 {allowed}")

        table_name = self.TABLE_MAP[adjust_type]
        adj = "" if adjust_type == "bfq" else adjust_type

        self.db_manager.connect()
        self.db_manager.create_table(table_name)

        collector = StockDataCollector(data_source, adj)
        all_stocks = self.stock_list_provider.get_stock_list()

        if all_stocks is None or all_stocks.empty:
            print("❌ 无法获取股票列表")
            return

        if "stock_code" not in all_stocks.columns or "stock_name" not in all_stocks.columns:
            print("❌ parquet 文件必须包含 stock_code 和 stock_name 列")
            return

        all_stocks["stock_code"] = all_stocks["stock_code"].astype(str).str.zfill(6)
        all_stocks["stock_name"] = all_stocks["stock_name"].astype(str)

        last_date_map = self.db_manager.get_last_dates(table_name)
        task_list = []

        for _, row in all_stocks.iterrows():
            code = row.stock_code
            name = row.stock_name
            last = last_date_map.get(code)
            start = "2014-01-01" if not last else (datetime.strptime(last, "%Y-%m-%d") + timedelta(1)).strftime("%Y-%m-%d")
            if start > self.target_date:
                continue
            task_list.append((code, name, start))

        success = skip = fail = 0
        import threading
        lock = threading.Lock()

        def worker(code, name, start):
            nonlocal success, fail
            try:
                df = collector.get_stock_data(code, start, self.target_date)
                if df is None or df.empty:
                    return "skip"
                ok = self.db_manager.insert_batch(df, table_name, code, name)
                return "ok" if ok else "fail"
            except:
                return "fail"

        print(f"\n🚀 启动多线程，线程数：{self.max_workers}")
        from tqdm import tqdm
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(worker, c, n, s): (c, n, s) for c, n, s in task_list}
            pbar = tqdm(as_completed(futures), total=len(futures), desc="极速同步中", unit="只")

            for f in pbar:
                res = f.result()
                with lock:
                    if res == "ok":
                        success += 1
                    elif res == "skip":
                        skip += 1
                    else:
                        fail += 1
                if success % self.batch_commit == 0:
                    self.db_manager.commit()
                pbar.set_postfix({"成功": success, "跳过": skip, "失败": fail})

        self.db_manager.commit()
        self.db_manager.close()
        print(f"\n✅ 极速同步完成！成功：{success} | 跳过：{skip} | 失败：{fail}")