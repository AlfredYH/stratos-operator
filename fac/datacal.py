import talib
import pandas as pd
import numpy as np
from ..utils.getdata_fromsqlite import get_stock_history
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List


def _format_stock_code(code) -> str:
    """将股票代码强制定义为6位数字字符串"""
    code_str = str(code).strip()
    code_str = ''.join(filter(str.isdigit, code_str))
    if len(code_str) < 6:
        code_str = code_str.zfill(6)
    elif len(code_str) > 6:
        code_str = code_str[:6]
    return code_str


def process_single_stock(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    处理单只股票的技术指标计算
    :param stock_code: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 处理后的DataFrame，包含date, stock_code和所有技术指标
    """
    stock_code = _format_stock_code(stock_code)
    
    try:
        df = get_stock_history(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            adj_type="qfq"
        )
        
        if df is None or len(df) < 40:
            return None
        
        df = _execute_pipeline(df)
        df = df.dropna()
        
        if df.empty:
            return None
        
        df = df.reset_index()
        df.rename(columns={'index': 'date'}, inplace=True)
        df['stock_code'] = stock_code
        
        cols = ['date', 'stock_code'] + [c for c in df.columns if c not in ['date', 'stock_code']]
        df = df[cols]
        
        return df
    except Exception as e:
        print(f"处理股票 {stock_code} 失败: {e}")
        return None


def _execute_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """流水线式触发各指标计算"""
    df = _calc_price_dif(df)
    df = _calc_macd(df)
    df = _calc_ma(df)
    df = _calc_bollinger_bands(df)
    df = _calc_bb_percent(df)
    df = _calc_volume_log(df)
    df = _calc_volume_feature(df)
    df = _calc_target_label(df)
    df = df.copy()
    return df


def _calc_price_dif(df: pd.DataFrame) -> pd.DataFrame:
    """计算价格差"""
    df['price_dif_max'] = df['high'] - df['low']
    df['price_dif'] = df['close'] - df['open']
    return df


def _calc_macd(df: pd.DataFrame) -> pd.DataFrame:
    """计算标准MACD"""
    close = np.asarray(df['close'].values, dtype=np.float64)
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macd_signal'] = macdsignal
    df['macd_hist'] = macdhist
    df['macd_slope'] = talib.LINEARREG_SLOPE(macd, timeperiod=3)
    return df


def _calc_ma(df: pd.DataFrame) -> pd.DataFrame:
    """计算归一化的均线特征"""
    close = np.asarray(df['close'].values, dtype=np.float64)
    ma5 = talib.MA(close, timeperiod=5)
    ma16 = talib.MA(close, timeperiod=16)
    ma243 = talib.MA(close, timeperiod=243)
    
    close_arr = np.asarray(df['close'].values, dtype=np.float64)
    df['ma5_bias'] = (close_arr / ma5) - 1
    df['ma16_rel'] = (ma16 / ma5) - 1
    df['ma243_bias'] = (close_arr / ma243) - 1
    df['ma_spread'] = (ma5 / ma16) - 1
    return df


def _calc_bollinger_bands(df: pd.DataFrame, period: int = 20, nbdev: int = 2) -> pd.DataFrame:
    """计算布林带上下轨"""
    close = np.asarray(df['close'].values, dtype=np.float64)
    upper, middle, lower = talib.BBANDS(
        close, 
        timeperiod=period, 
        nbdevup=nbdev, 
        nbdevdn=nbdev
    )
    df['bb_upper'] = upper
    df['bb_lower'] = lower
    df['bb_width'] = upper - lower
    df['bb_div'] = (upper - lower) / (middle + 1e-9)
    df['bb_width_slope'] = talib.LINEARREG_SLOPE(df['bb_width'].values.astype(np.float64), timeperiod=4)
    return df


def _calc_bb_percent(df: pd.DataFrame) -> pd.DataFrame:
    """计算收盘价在布林带中的偏移比例"""
    if 'bb_upper' not in df.columns:
        df = _calc_bollinger_bands(df)
    close = np.asarray(df['close'].values, dtype=np.float64)
    upper = np.asarray(df['bb_upper'].values, dtype=np.float64)
    lower = np.asarray(df['bb_lower'].values, dtype=np.float64)
    # 计算收盘价在布林带中的偏移比例，范围一般在 -1 到 1 之间
    df['bb_close_div'] = (2 * close - (close + lower)) / (upper - lower + 1e-9)
    return df


def _calc_volume_log(df: pd.DataFrame) -> pd.DataFrame:
    """计算成交量的对数变换"""
    df['volume_log'] = np.log(df['volume'] + 1)
    return df


def _calc_volume_feature(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算成交量Z-Score"""
    v_log = np.log(df['volume'] + 1)
    v_ma = v_log.rolling(period).mean()
    v_std = v_log.rolling(period).std()
    df['volume_z'] = (v_log - v_ma) / (v_std + 1e-9)
    return df


def _calc_target_label(df: pd.DataFrame, forward_days: int = 5) -> pd.DataFrame:
    """计算作为Label的未来收益率"""
    df['target'] = df['close'].shift(-forward_days) / df['close'] - 1
    return df


def process_stocks_from_csv(
    csv_path: str, 
    start_date: str, 
    end_date: str, 
    max_workers: int = 20
) -> pd.DataFrame:
    """
    从CSV文件读取股票代码列表，多线程处理所有股票的技术指标
    :param csv_path: 包含stock_code列的CSV文件路径
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param max_workers: 最大线程数，默认20
    :return: 合并后的DataFrame，包含所有股票的date, stock_code和技术指标
    """
    stock_df = pd.read_csv(csv_path, dtype={'stock_code': str})
    
    if 'stock_code' not in stock_df.columns:
        if len(stock_df.columns) == 1:
            stock_df.columns = ['stock_code']
        else:
            raise ValueError("CSV文件必须包含stock_code列")
    
    stock_codes = stock_df['stock_code'].apply(_format_stock_code).unique().tolist()
    
    print(f"共 {len(stock_codes)} 只股票待处理")
    
    all_results = []
    completed = 0
    total = len(stock_codes)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_stock, code, start_date, end_date): code
            for code in stock_codes
        }
        
        for future in as_completed(futures):
            completed += 1
            code = futures[future]
            result = future.result()
            if result is not None:
                all_results.append(result)
                print(f"[{completed}/{total}] ✓ {code} 处理成功")
            else:
                print(f"[{completed}/{total}] ✗ {code} 处理失败")
    
    if not all_results:
        return pd.DataFrame()
    
    final_df = pd.concat(all_results, axis=0, ignore_index=True)
    final_df = final_df.sort_values(['stock_code', 'date']).reset_index(drop=True)
    
    print(f"\n数据处理完成，共 {len(final_df)} 条记录")
    return final_df


class StockFeatureProcessor:
    def __init__(self, stock_code, start_date, end_date):
        self.stock_code = stock_code
        try:
            self.df = get_stock_history(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if self.df is None or len(self.df) < 40:
                self.df = pd.DataFrame()
                return
                
            self._execute_pipeline()
        except Exception as e:
            print(f"读取股票 {stock_code} 失败: {e}")
            self.df = pd.DataFrame()

    def _execute_pipeline(self):
        """流水线式触发各指标计算"""
        self.df = _execute_pipeline(self.df)
        self.df.dropna(inplace=True)

    def get_processed_df(self):
        """获取处理后的DataFrame"""
        return self.df
