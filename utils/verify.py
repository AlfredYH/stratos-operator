import sys
import os

# 将项目根目录加入路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
import akshare as ak
import tushare as ts
from datetime import datetime, timedelta

from utils.datacollect_config import get_config
from utils.getdata_fromsqlite import get_stock_history as get_from_sqlite
from utils.data_collect import StockDataCollector


def normalize_stock_code(stock_code: str) -> str:
    """标准化股票代码，添加交易所前缀"""
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


def get_from_akshare(stock_code: str, start_date: str, end_date: str, adj_type: str = "") -> pd.DataFrame:
    """从Akshare获取股票数据"""
    try:
        normalized_code = normalize_stock_code(stock_code)
        df = ak.stock_zh_a_daily(
            symbol=normalized_code,
            start_date=start_date,
            end_date=end_date,
            adjust=adj_type
        )
        if df is None or df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"❌ Akshare 获取失败: {e}")
        return pd.DataFrame()


def get_from_tushare(stock_code: str, start_date: str, end_date: str, adj_type: str = "none") -> pd.DataFrame:
    """从Tushare获取股票数据"""
    try:
        cfg = get_config()
        token = cfg.tushare_token
        if not token:
            print("❌ 未配置Tushare Token")
            return pd.DataFrame()
        
        ts.set_token(token)
        ts_pro = ts.pro_api()
        
        ts_code = f"{stock_code.zfill(6)}.SH" if stock_code.startswith(('6', '9')) else f"{stock_code.zfill(6)}.SZ"
        
        df = ts_pro.daily(
            ts_code=ts_code,
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adj=adj_type
        )
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        df['date'] = pd.to_datetime(df['trade_date'])
        df.set_index('date', inplace=True)
        df['volume'] = df['vol'] * 100
        df = df.sort_index(ascending=True)
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"❌ Tushare 获取失败: {e}")
        return pd.DataFrame()


def compare_data(df1: pd.DataFrame, df2: pd.DataFrame, name1: str, name2: str) -> dict:
    """比较两个DataFrame的数据差异"""
    if df1.empty and df2.empty:
        return {"一致": True, "差异": "两者都为空"}
    
    if df1.empty:
        return {"一致": False, "差异": f"{name1}为空，{name2}有{len(df2)}条"}
    
    if df2.empty:
        return {"一致": False, "差异": f"{name1}有{len(df1)}条，{name2}为空"}
    
    # 对齐索引
    common_dates = df1.index.intersection(df2.index)
    if len(common_dates) == 0:
        return {"一致": False, "差异": "无共同交易日"}
    
    df1_aligned = df1.loc[common_dates]
    df2_aligned = df2.loc[common_dates]
    
    # 比较价格差异
    diff_results = {}
    for col in ['open', 'high', 'low', 'close']:
        if col in df1_aligned.columns and col in df2_aligned.columns:
            # 允许0.01的误差（可能是浮点精度问题）
            diff = (df1_aligned[col] - df2_aligned[col]).abs()
            max_diff = diff.max() if len(diff) > 0 else 0
            diff_results[col] = max_diff
    
    is_consistent = all(v < 0.01 for v in diff_results.values())
    
    return {
        "一致": is_consistent,
        "共同交易日": len(common_dates),
        "差异详情": diff_results
    }


def verify_stock_data(stock_code: str, start_date: str = None, end_date: str = None, adj_type: str = "qfq"):
    """
    验证股票数据一致性
    
    Args:
        stock_code: 股票代码，如 "002110"
        start_date: 开始日期，默认为30天前
        end_date: 结束日期，默认为今天
        adj_type: 复权类型，可选 qfq(前复权)、hfq(后复权)、bfq(不复权)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"📊 数据验证: {stock_code} | {start_date} ~ {end_date} | {adj_type}")
    print(f"{'='*60}")
    
    # 获取三个数据源的数据
    print(f"\n🔄 正在从三个数据源获取数据...")
    
    # 1. Akshare
    print(f"  → 获取 Akshare 数据...")
    adj_param = "" if adj_type == "bfq" else adj_type
    df_ak = get_from_akshare(stock_code, start_date, end_date, adj_param)
    print(f"    获得 {len(df_ak)} 条记录")
    
    # 2. Tushare
    print(f"  → 获取 Tushare 数据...")
    tushare_adj = "none" if adj_type == "bfq" else adj_type
    df_ts = get_from_tushare(stock_code, start_date, end_date, tushare_adj)
    print(f"    获得 {len(df_ts)} 条记录")
    
    # 3. SQLite
    print(f"  → 获取 SQLite 数据...")
    df_sqlite = get_from_sqlite(stock_code, start_date, end_date, adj_type)
    print(f"    获得 {len(df_sqlite)} 条记录")
    
    # 比较数据
    print(f"\n{'='*60}")
    print(f"📈 数据对比结果:")
    print(f"{'='*60}")
    
    # Akshare vs Tushare
    print(f"\n[1] Akshare vs Tushare:")
    result_at = compare_data(df_ak, df_ts, "Akshare", "Tushare")
    if result_at["一致"]:
        print(f"  ✅ 一致 (共同交易日: {result_at.get('共同交易日', 0)})")
    else:
        print(f"  ❌ 不一致: {result_at['差异']}")
        if "差异详情" in result_at:
            for k, v in result_at["差异详情"].items():
                print(f"     {k}: 最大差异 {v:.4f}")
    
    # Akshare vs SQLite
    print(f"\n[2] Akshare vs SQLite:")
    result_as = compare_data(df_ak, df_sqlite, "Akshare", "SQLite")
    if result_as["一致"]:
        print(f"  ✅ 一致 (共同交易日: {result_as.get('共同交易日', 0)})")
    else:
        print(f"  ❌ 不一致: {result_as['差异']}")
        if "差异详情" in result_as:
            for k, v in result_as["差异详情"].items():
                print(f"     {k}: 最大差异 {v:.4f}")
    
    # Tushare vs SQLite
    print(f"\n[3] Tushare vs SQLite:")
    result_ts = compare_data(df_ts, df_sqlite, "Tushare", "SQLite")
    if result_ts["一致"]:
        print(f"  ✅ 一致 (共同交易日: {result_ts.get('共同交易日', 0)})")
    else:
        print(f"  ❌ 不一致: {result_ts['差异']}")
        if "差异详情" in result_ts:
            for k, v in result_ts["差异详情"].items():
                print(f"     {k}: 最大差异 {v:.4f}")
    
    # 打印数据样本
    print(f"\n{'='*60}")
    print(f"📋 数据样本 (最近5天):")
    print(f"{'='*60}")
    
    if not df_ak.empty:
        print(f"\nAkshare:")
        print(df_ak.tail())
    if not df_ts.empty:
        print(f"\nTushare:")
        print(df_ts.tail())
    if not df_sqlite.empty:
        print(f"\nSQLite:")
        print(df_sqlite.tail())
    
    return {
        "akshare": df_ak,
        "tushare": df_ts,
        "sqlite": df_sqlite,
        "result_at": result_at,
        "result_as": result_as,
        "result_ts": result_ts
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="验证股票日线数据一致性")
    parser.add_argument("stock_code", type=str, nargs="?", default="002110", help="股票代码，如 002110")
    parser.add_argument("--start", type=str, default="2025-12-23", help="开始日期，如 2024-01-01")
    parser.add_argument("--end", type=str, default="2026-02-21", help="结束日期，如 2024-12-31")
    parser.add_argument("--adj", type=str, default="qfq", choices=["qfq", "hfq", "bfq"], help="复权类型")
    
    args = parser.parse_args()
    
    verify_stock_data(args.stock_code, args.start, args.end, args.adj)