# 行业轮动选股 - Tushare 版本
# 这个版本使用 Tushare Pro 替代 Akshare 获取数据，适合 Akshare 接口不稳定时使用。
# 需要提前在 key.yaml 中配置 TUSHARE_TOKEN

import tushare as ts
import pandas as pd
import numpy as np
import os
from datetime import datetime
import yaml

# ====================== 填写你的 Tushare Token ======================
with open("./select/key.yaml", "r") as f:
    TUSHARE_TOKEN = yaml.safe_load(f)["client"]["TUSHARE_TOKEN"]
# ====================================================================

class IndustryRotationTushare:
    def __init__(self):
        ts.set_token(TUSHARE_TOKEN)
        self.pro = ts.pro_api()
        self.data_dir = "./industry_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 轮动权重
        self.weights = {
            "momentum": 0.4,
            "main_flow": 0.2,
            "north_flow": 0.2,
            "amount_ratio": 0.2
        }

    def get_sw_industry_list(self):
        """获取申万一级行业列表"""
        df = self.pro.index_classify(level='L1', src='SW')
        return df

    def get_industry_daily(self, trade_date=None):
        """获取申万行业指数行情 + 涨跌幅"""
        ind_df = self.pro.index_classify(level='L1', src='SW')
        all_data = []

        for _, row in ind_df.iterrows():
            try:
                df = self.pro.index_daily(ts_code=row['index_code'], start_date=trade_date, end_date=trade_date)
                if not df.empty:
                    df['industry'] = row['industry_name']
                    all_data.append(df)
            except Exception as e:
                continue

        if all_data:
            df = pd.concat(all_data, ignore_index=True)
            df['pct_chg'] = df['pct_chg'].fillna(0)
            return df
        return pd.DataFrame()

    def get_main_moneyflow(self, trade_date):
        """行业资金流向（主力）"""
        try:
            df = self.pro.moneyflow_hsgt(trade_date=trade_date.replace('-', ''))
            return df
        except:
            return pd.DataFrame()

    def get_north_industry(self):
        """北向行业持仓 & 净流入"""
        try:
            df = self.pro.hsgt_industry()
            return df
        except:
            return pd.DataFrame()

    def cross_rank(self, s):
        """截面打分 0~1"""
        return s.rank(pct=True, ascending=True)

    def run_rotation(self, trade_date=None):
        """执行行业轮动打分"""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")

        print("=== 正在获取行业行情 ===")
        df_price = self.get_industry_daily(trade_date=trade_date)

        print("=== 正在获取北向资金 ===")
        df_north = self.get_north_industry()

        print("=== 正在获取主力资金 ===")
        df_main = self.get_main_moneyflow(trade_date=trade_date)

        # 合并
        df = df_price.copy()
        df = df.merge(df_north[['industry', 'net_amount']], on='industry', how='left')
        df = df.rename(columns={'net_amount': 'north_net'})

        # 打分
        df['momentum_score'] = self.cross_rank(df['pct_chg'])
        df['north_score'] = self.cross_rank(df['north_net'].fillna(0))
        df['amount_score'] = self.cross_rank(df['amount'].fillna(0))

        # 综合轮动得分
        df['total_score'] = (
            self.weights['momentum'] * df['momentum_score'] +
            self.weights['north_flow'] * df['north_score'] +
            self.weights['amount_ratio'] * df['amount_score']
        )

        df = df.sort_values('total_score', ascending=False)

        # 输出
        print("\n===== 行业轮动 TOP10 =====")
        print(df[['industry', 'total_score', 'pct_chg', 'north_score']].head(10))

        # 保存 parquet
        save_path = os.path.join(self.data_dir, "industry_rotation_tushare.parquet")
        df.to_parquet(save_path, index=False)
        print(f"\n✅ 已保存至 {save_path}")

        return df

if __name__ == "__main__":
    rot = IndustryRotationTushare()
    df_result = rot.run_rotation()
    print("\n🎯 推荐关注 TOP5 行业：")
    print(df_result.head(5)['industry'].tolist())