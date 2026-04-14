import os
import yaml
import numpy as np
import pandas as pd
import talib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# ======================== 路径配置 ========================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ROOT, "fac_config.yaml")
STOCK_POOL_PATH = os.path.join(ROOT, "utils", "stock_pool.parquet")
# 筛选过后的股票就从filter文件夹里读取，防止后续改动导致股票池丢失
# STOCK_POOL_PATH = os.path.join(ROOT, "filter", "stock_pool.parquet")

# 加载配置
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

from quant.factors import FACTOR_REGISTRY

ENABLED_FACTORS = config["enabled_factors"]
PARAMS = config["params"]
PRE_PROCESS = config["pre_process"]
FEATURE_COLS = config["gplearn_input_features"]

# 导入数据获取函数
try:
    from ..utils.getdata_fromsqlite import get_stock_history
except Exception as e:
    print(f"get_stock_history 导入失败: {e}")


# ======================== 【防坑核心】股票代码格式化 ========================
def _format_stock_code(code) -> str:
    code_str = str(code).strip()
    code_str = code_str.split(".")[0]
    code_str = "".join(filter(str.isdigit, code_str))
    return code_str.zfill(6)


def apply_cross_section_process(df: pd.DataFrame, feature_cols):
    df = df.copy()
    q_low, q_high = PRE_PROCESS["winsorize_quantile"]

    for col in feature_cols:
        if col not in df.columns:
            continue

        if PRE_PROCESS["winsorize"]:
            def winsorize(x):
                lo, hi = x.quantile([q_low, q_high])
                return x.clip(lo, hi)
            df[col] = df.groupby("date")[col].transform(winsorize)

        if PRE_PROCESS["cross_section_normalize"]:
            def normalize(x):
                return (x - x.mean()) / (x.std() + 1e-8)
            df[col] = df.groupby("date")[col].transform(normalize)
    return df


def compute_all_factors(df):
    df = df.copy()
    for name in ENABLED_FACTORS:
        if name in FACTOR_REGISTRY:
            df = FACTOR_REGISTRY[name](df, PARAMS)
    return df


def process_single_stock(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    code = _format_stock_code(stock_code)
    try:
        df = get_stock_history(
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            adj_type="qfq"
        )
        if df is None or len(df) < 40:
            return None

        df = compute_all_factors(df)
        df = df.dropna()
        if df.empty:
            return None

        df = df.reset_index().rename(columns={"index": "date"})
        df["stock_code"] = code
        cols = ["date", "stock_code"] + [c for c in df.columns if c not in ["date", "stock_code"]]
        return df[cols]
    except Exception as e:
        print(f"[{code}] 处理失败: {e}")
        return None


# ======================== 从 parquet 读取股票池（防丢0版本） ========================
def process_stocks_from_parquet(start_date: str, end_date: str, max_workers: int = 20):
    stock_df = pd.read_parquet(
        STOCK_POOL_PATH,
        dtype={"stock_code": str}
    )

    if "stock_code" not in stock_df.columns:
        raise ValueError("parquet 文件必须包含 stock_code 列")

    codes = stock_df["stock_code"].apply(_format_stock_code).unique().tolist()
    all_results = []

    print(f"从 parquet 加载股票池，共 {len(codes)} 只")

    with ThreadPoolExecutor(max_workers) as executor:
        future_map = {
            executor.submit(process_single_stock, c, start_date, end_date): c
            for c in codes
        }

        for i, future in enumerate(as_completed(future_map)):
            code = future_map[future]
            res = future.result()
            if res is not None:
                all_results.append(res)
                print(f"[{i+1}/{len(codes)}] ✓ {code} 成功")
            else:
                print(f"[{i+1}/{len(codes)}] ✗ {code} 失败")

    if not all_results:
        return pd.DataFrame()

    final = pd.concat(all_results, ignore_index=True)
    final = final.sort_values(["stock_code", "date"]).reset_index(drop=True)
    final = apply_cross_section_process(final, FEATURE_COLS)
    return final