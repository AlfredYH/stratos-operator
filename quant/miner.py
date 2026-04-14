import os
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from gplearn.genetic import SymbolicTransformer
from quant.datacal import process_stocks_from_parquet

# 路径与配置
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ROOT, "fac_config.yaml")

with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

FEATURE_COLS = config["gplearn_input_features"]
GP_CFG = config["gplearn"]
PLOT_RESULT = config["plot_result"]
RECORD_MODE = config["record_mode"]


class GPAlphaMiner:
    def __init__(self):
        self.scaler = StandardScaler()
        self.gp = SymbolicTransformer(
            generations=GP_CFG["generations"],
            population_size=GP_CFG["population_size"],
            n_components=GP_CFG["n_components"],
            function_set=GP_CFG["function_set"],
            metric="spearman",
            parsimony_coefficient=GP_CFG["parsimony_coefficient"],
            verbose=1,
            random_state=42,
            n_jobs=-1
        )
        self.best_programs = None

    def preprocess_data(self, df):
        df = df.dropna(subset=FEATURE_COLS + ["target"])
        X = df[FEATURE_COLS].values
        y = df["target"].values
        return X, y, df

    def fit(self, df):
        X, y, _ = self.preprocess_data(df)
        print(f"\n训练样本数: {len(X)}")
        X_scaled = self.scaler.fit_transform(X)
        self.gp.fit(X_scaled, y)
        self.best_programs = self.gp._best_programs

        print("\n" + "=" * 60)
        print("最优因子公式")
        print("=" * 60)
        for i, prog in enumerate(self.best_programs):
            print(f"Alpha_{i:02d}: {prog}")

    def evaluate(self, df):
        if not PLOT_RESULT:
            print("\n绘图已关闭（plot_result = false）")
            return

        X, y, _ = self.preprocess_data(df)
        X_scaled = self.scaler.transform(X)
        factors = self.gp.transform(X_scaled)
        top_factor = factors[:, 0]

        lo, hi = np.percentile(top_factor, [2.5, 97.5])
        top_factor = np.clip(top_factor, lo, hi)

        ic, _ = spearmanr(top_factor, y)
        res = pd.DataFrame({"factor": top_factor, "ret": y})
        res["group"] = pd.qcut(res["factor"], 5, labels=["G1", "G2", "G3", "G4", "G5"])
        group_mean = res.groupby("group")["ret"].mean()

        plt.figure(figsize=(10, 5))
        sns.barplot(x=group_mean.index, y=group_mean.values, palette="RdYlGn")
        plt.title(f"Factor Group Return | IC = {ic:.4f}")
        plt.tight_layout()
        plt.show()

    def save_factors_and_formulas(self, df):
        """保存因子数据 + 最优公式"""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        save_cols = ["date", "stock_code"] + FEATURE_COLS + ["target"]
        df_out = df[save_cols].copy()

        # ---------------------
        # 1. 保存因子数据
        # ---------------------
        latest_factor_path = os.path.join(ROOT, "factordata.parquet")
        df_out.to_parquet(latest_factor_path, index=False)
        print(f"\n已保存最新因子: {latest_factor_path}")

        if RECORD_MODE:
            hist_factor_path = os.path.join(ROOT, f"{timestamp}_factordata.parquet")
            df_out.to_parquet(hist_factor_path, index=False)
            print(f"已保存历史因子: {hist_factor_path}")

        # ---------------------
        # 2. 保存最优公式
        # ---------------------
        formula_lines = [
            "=" * 60,
            f"GP 最优因子公式 | 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]
        for i, prog in enumerate(self.best_programs):
            formula_lines.append(f"Alpha_{i:02d}: {prog}")

        formula_text = "\n".join(formula_lines)
        latest_formula_path = os.path.join(ROOT, "best_formulas.txt")

        with open(latest_formula_path, "w", encoding="utf-8") as f:
            f.write(formula_text)
        print(f"已保存最新公式: {latest_formula_path}")

        if RECORD_MODE:
            hist_formula_path = os.path.join(ROOT, f"{timestamp}_best_formulas.txt")
            with open(hist_formula_path, "w", encoding="utf-8") as f:
                f.write(formula_text)
            print(f"已保存历史公式: {hist_formula_path}")

    def miner_run(self, start_date, end_date):
        print("🚀 读取股票池并计算因子...")
        raw_df = process_stocks_from_parquet(start_date, end_date)

        print("\n🧬 开始 GP 因子挖掘...")
        self.fit(raw_df)

        print("\n📊 评估分组收益...")
        self.evaluate(raw_df)

        print("\n💾 保存结果...")
        self.save_factors_and_formulas(raw_df)

        print("\n🎉 全部完成！")


if __name__ == "__main__":
    miner = GPAlphaMiner()
    miner.miner_run(
        start_date="2023-01-01",
        end_date="2024-06-30"
    )