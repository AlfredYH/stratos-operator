import sqlite3
import pandas as pd
from queue import Queue
from threading import Lock
import os
from typing import Optional


# 数据库文件名
DB_NAME = "stockdata.db"


def _get_db_path() -> str:
    """获取数据库文件的完整路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, DB_NAME)


class SQLitePool(object):
    """
    SQLite 连接池，用于多线程并发查询
    """
    _instance = None
    _lock = Lock()
    _pool_size = 20

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLitePool, cls).__new__(cls)
                cls._instance.pool = Queue(maxsize=cls._pool_size)
                db_path = _get_db_path()
                for _ in range(cls._pool_size):
                    conn = sqlite3.connect(db_path, check_same_thread=False)
                    cls._instance.pool.put(conn)
        return cls._instance

    def get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return self.pool.get()

    def return_conn(self, conn: sqlite3.Connection) -> None:
        """归还数据库连接"""
        self.pool.put(conn)


def get_stock_history(
    stock_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adj_type: str = "qfq"
) -> pd.DataFrame:
    """
    从 SQLite 数据库获取股票历史K线数据

    Args:
        stock_code: 股票代码
        start_date: 开始日期，格式 YYYY-MM-DD 或 YYYYMMDD
        end_date: 结束日期，格式 YYYY-MM-DD 或 YYYYMMDD
        adj_type: 复权类型，可选 qfq(前复权)、hfq(后复权)、bfq(不复权)

    Returns:
        包含K线数据的DataFrame，失败返回空DataFrame
    """
    allowed = ("qfq", "hfq", "bfq")
    if adj_type not in allowed:
        raise ValueError(f"adj_type 必须是 {allowed}")

    table_name = f"daily_price_{adj_type}"
    pool = SQLitePool()
    conn = pool.get_conn()

    try:
        # 日期转换
        parsed_start = pd.to_datetime(start_date).strftime('%Y-%m-%d') if start_date else None
        parsed_end = pd.to_datetime(end_date).strftime('%Y-%m-%d') if end_date else None

        # 构建查询
        query = f"SELECT * FROM {table_name} WHERE stock_code = ?"
        params = [stock_code]

        if parsed_start:
            query += " AND trade_date >= ?"
            params.append(parsed_start)
        if parsed_end:
            query += " AND trade_date <= ?"
            params.append(parsed_end)

        query += " ORDER BY trade_date ASC"

        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            return pd.DataFrame()

        # 列顺序调整：stock_code, stock_name 放在最前面
        fixed_cols = ['stock_code', 'stock_name']
        other_cols = [c for c in df.columns if c not in fixed_cols and c != 'trade_date']
        new_column_order = fixed_cols + other_cols

        # 处理日期索引
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        df.index.name = 'date'

        return df[new_column_order]

    except Exception as e:
        print(f"❌ 查询 {stock_code} ({adj_type}) 失败: {e}")
        return pd.DataFrame()
    finally:
        pool.return_conn(conn)


if __name__ == "__main__":
    # 测试示例
    adj_type = "bfq"
    stock_data = get_stock_history(
        stock_code="002110",
        start_date="20241215",
        end_date="2026-03-15",
        adj_type=adj_type
    )

    if not stock_data.empty:
        print(f"✅ 成功获取数据，价格类型：{adj_type}")
        print("============================= 数据预览 =============================")
        print(stock_data.tail())
    else:
        print("❌ 未获取到有效数据")