import sqlite3
import pandas as pd
from queue import Queue
from threading import Lock
import os


# 配置信息
DB_NAME = "stockdata.db"

def full_path():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_full_path = os.path.join(script_dir, DB_NAME)
    # csv_full_path = os.path.join(script_dir, CSV_NAME)

    return db_full_path


class SQLitePool():
    """简单的 SQLite 连接池实现"""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLitePool, cls).__new__(cls)
                cls._instance.pool = Queue(maxsize=20)
                for _ in range(20):
                    # check_same_thread=False 是多线程并发查询的关键
                    conn = sqlite3.connect(full_path(), check_same_thread=False)
                    cls._instance.pool.put(conn)
        return cls._instance

    def get_conn(self):
        return self.pool.get()

    def return_conn(self, conn):
        self.pool.put(conn)

def get_stock_history(stock_code: str, 
                      start_date: str = None, 
                      end_date: str = None,
                      adj_type: str = "qfq") -> pd.DataFrame:
    """
    优化后的查询函数
    :param adj_type: 复权类型，'qfq' 对应前复权表，'bfq' 对应不复权表
    """
    # 自动根据参数定义表名
    table_name = f"daily_price_{adj_type}"
    
    pool = SQLitePool()
    conn = pool.get_conn()
    
    try:
        # 1. 极简日期转换
        parsed_start = pd.to_datetime(start_date).strftime('%Y-%m-%d') if start_date else None
        parsed_end = pd.to_datetime(end_date).strftime('%Y-%m-%d') if end_date else None

        # 2. 参数化查询
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

        # 3. 列顺序调整：将 stock_code, stock_name 放在最前面
        fixed_cols = ['stock_code', 'stock_name']
        # 获取除了固定列和日期列之外的其他所有列
        other_cols = [c for c in df.columns if c not in fixed_cols and c != 'trade_date']
        # 重新组合列顺序
        new_column_order = fixed_cols + other_cols
        
        # 4. 后处理优化
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        df.index.name = 'date'
        
        # 返回指定顺序的 DataFrame
        return df[new_column_order]

    except Exception as e:
        print(f"❌ 查询 {stock_code} ({adj_type}) 失败: {e}")
        return pd.DataFrame()
    finally:
        pool.return_conn(conn)

# 测试示例
if __name__ == "__main__":
    # 测试：获取不复权数据 (bfq)
    adj_type = "bfq"
    stock_data = get_stock_history(
        stock_code="002110",
        start_date="20241215",
        end_date="2026-03-15",
        adj_type=adj_type  # 切换为不复权数据
    )
    
    if not stock_data.empty:
        print(f"✅ 成功获取数据，价格类型：{adj_type}")
        print("================================= 数据预览 =================================")
        print(stock_data.tail())
    else:
        print("❌ 未获取到有效数据")