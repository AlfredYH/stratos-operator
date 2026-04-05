import os
import akshare as ak
import pandas as pd
from tqdm import tqdm
import sqlite3
import yaml
from datetime import datetime, timedelta, date
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .data_collect import DataConfig, StockDataCollector
except ImportError:
    print("❌ 错误：找不到 data_collect.py，请确保该文件在当前目录下。")
    exit()

# ===================== 1. 基础配置 =====================
DB_NAME = "stockdata.db"
TARGET_DATE = date.today().strftime("%Y-%m-%d")
CSV_NAME = "all_stock_list.csv"

# ===================== 🔥 加速配置 =====================
MAX_WORKERS = 4     # 线程数，根据网络调整 8~32
BATCH_COMMIT = 100    # 每 N 条提交一次

def full_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_full_path = os.path.join(script_dir, DB_NAME)
    csv_full_path = os.path.join(script_dir, CSV_NAME)
    return db_full_path, csv_full_path

class DailyUpdate:
    def __init__(self):
        self.db_path, self.csv_path = full_path()
        self.conn = None
        self.cursor = None
        self.table_name = None

    def get_all_stock_list(self):
        try:
            print("正在获取沪深京A股股票列表...")
            stock_df = ak.stock_info_a_code_name()
            stock_df["代码"] = stock_df["代码"].astype(str).str.zfill(6)
            stock_df.rename(columns={"代码": "stock_code", "名称": "stock_name"}, inplace=True)
            stock_df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            print("✅ 成功保存股票列表到CSV")
            return stock_df
        except Exception as e:
            print(f"⚠️ Akshare 失败，切换备用接口 Tushare: {e}")
            try:
                import tushare as ts
                config_full_path = os.path.join(os.path.dirname(__file__), "key.yaml")
                with open(config_full_path, "r", encoding="utf-8") as f:
                    tushare_token = yaml.safe_load(f)["client"]["TUSHARE_TOKEN"]
                ts.set_token(tushare_token)
                stock_df = ts.pro_api().stock_basic(exchange='', list_status='L', fields='symbol,name')
                stock_df.rename(columns={"symbol":"stock_code","name":"stock_name"}, inplace=True)
                stock_df["stock_code"] = stock_df["stock_code"].astype(str).str.zfill(6)
                stock_df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
                print("✅ Tushare 保存成功")
                return stock_df
            except Exception as e2:
                print(f"❌ 全部接口失败: {e2}")
                return None

    def init_db(self, table_name):
        self.table_name = table_name
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        # ===================== 🔥 极速优化 =====================
        self.cursor.execute("PRAGMA synchronous = OFF")       # 不等待磁盘写入
        self.cursor.execute("PRAGMA journal_mode = WAL")      # 读写并发
        self.cursor.execute("PRAGMA cache_size = -100000")    # 100MB 缓存
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        self.cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            trade_date DATE, stock_code TEXT, stock_name TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        );""")
        self.cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_cd ON {self.table_name}(stock_code, trade_date);")
        self.conn.commit()

    def get_all_last_dates(self):
        try:
            self.cursor.execute(f"SELECT stock_code, MAX(trade_date) FROM {self.table_name} GROUP BY stock_code")
            return {code: dt for code, dt in self.cursor.fetchall()}
        except:
            return {}

    def insert_batch(self, df, stock_code, stock_name):
        try:
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["stock_code"] = stock_code
            df["stock_name"] = stock_name
            df.rename(columns={"date":"trade_date"}, inplace=True)
            df.to_sql(self.table_name, self.conn, if_exists="append", index=False)
            return True
        except:
            return False

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ===================== 🔥 多线程极速同步 =====================
    def run_sync_process(self, data_source="akshare", adjust_type="bfq", debug_mode=False):
        allowed = ("qfq","hfq","bfq")
        if adjust_type not in allowed:
            raise ValueError(f"adjust_type 必须是 {allowed}")

        table = {
            "bfq":"daily_price_bfq",
            "qfq":"daily_price_qfq",
            "hfq":"daily_price_hfq"
        }[adjust_type]

        adj = "" if adjust_type == "bfq" else adjust_type
        self.init_db(table)

        config = DataConfig()
        config.update_config(data_source=data_source, adjust_type=adj, debug_mode=debug_mode)
        collector = StockDataCollector(config)

        try:
            all_stocks = pd.read_csv(self.csv_path, dtype={"stock_code":str,"stock_name":str})
        except:
            print("❌ 请先运行 get_all_stock_list()")
            return

        last_date_map = self.get_all_last_dates()
        task_list = []

        for _, row in all_stocks.iterrows():
            code = row.stock_code
            name = row.stock_name
            last = last_date_map.get(code)
            start = "2014-01-01" if not last else (datetime.strptime(last,"%Y-%m-%d")+timedelta(1)).strftime("%Y-%m-%d")
            if start > TARGET_DATE:
                continue
            task_list.append((code, name, start))

        success = skip = fail = 0
        lock = threading.Lock()

        def worker(code, name, start):
            nonlocal success, fail
            try:
                df = collector.get_stock_data(code, start, TARGET_DATE)
                if df is None or df.empty:
                    return "skip"
                ok = self.insert_batch(df, code, name)
                return "ok" if ok else "fail"
            except:
                return "fail"

        print(f"\n🚀 启动多线程，线程数：{MAX_WORKERS}")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(worker, c, n, s): (c,n,s) for c,n,s in task_list}
            pbar = tqdm(as_completed(futures), total=len(futures), desc="极速同步中", unit="只")

            for f in pbar:
                res = f.result()
                with lock:
                    if res == "ok": success +=1
                    elif res == "skip": skip +=1
                    else: fail +=1
                if success % BATCH_COMMIT == 0:
                    self.commit()
                pbar.set_postfix({"成功":success,"跳过":skip,"失败":fail})

        self.commit()
        self.close()
        print(f"\n✅ 极速同步完成！成功：{success} | 跳过：{skip} | 失败：{fail}")