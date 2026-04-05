
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from gplearn.genetic import SymbolicTransformer
from .datacal import process_stocks_from_csv


class GPAlphaMiner():
    def __init__(self, feature_cols, n_components=10, generations=60, population_size=4000):
        self.feature_cols = feature_cols
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.gp = SymbolicTransformer(
            generations=generations,
            population_size=population_size,
            n_components=n_components,
            function_set=['add', 'sub', 'mul', 'div', 'sqrt', 'log', 'abs', 'inv'],
            metric='spearman',
            parsimony_coefficient=0.001,
            verbose=1,
            random_state=42,
            n_jobs=-1
        )
        self.is_fitted = False

    def _cross_sectional_normalize(self, df):
        """核心改进：执行截面标准化"""
        df_scaled = df.copy()
        # 按日期分组，对每一天的特征执行 Z-Score
        # 即使某天市场大跌，当天的强弱关系依然被拉回到 0 均值附近
        for col in self.feature_cols:
            df_scaled[col] = df_scaled.groupby('date')[col].transform(
                lambda x: (x - x.mean()) / (x.std() + 1e-8)
            )
        return df_scaled

    def preprocess_data(self, df):
        """数据清洗与标准化流程"""
        # 1. 剔除无效值
        df = df.dropna(subset=self.feature_cols + ['target'])
        
        # 2. 截面归一化 (消除时间轴上的系统性噪音)
        print("正在进行截面标准化...")
        df = self._cross_sectional_normalize(df)
        
        # 3. 再次全局缩放 (确保输入 gplearn 的数据量纲完全统一)
        # 这一步是为了处理截面处理后可能存在的极小量纲差异
        X = df[self.feature_cols].values
        y = df['target'].values
        return X, y, df

    def fit(self, df):
        """训练模型"""
        X, y, _ = self.preprocess_data(df)
        print(f"开始进化，样本量: {len(X)}, 特征数: {len(self.feature_cols)}")
        
        # 这里的 scaler 存储了最终的缩放标准
        X_scaled = self.scaler.fit_transform(X)
        self.gp.fit(X_scaled, y)
        self.is_fitted = True
        
        print("\n" + "="*60)
        print("【挖掘出的最优因子公式】")
        for i, prog in enumerate(self.gp._best_programs):
            if prog: print(f"Alpha_{i:02d}: {prog}")
        print("="*60)

    def evaluate(self, df):
        """性能回测与可视化"""
        if not self.is_fitted:
            raise ValueError("模型尚未训练！")
            
        X, y, _ = self.preprocess_data(df)
        X_scaled = self.scaler.transform(X)
        new_factors = self.gp.transform(X_scaled)
        
        # 取最强因子
        top_factor = new_factors[:, 0]
        
        # 去极值处理 (Winsorize)
        lower, upper = np.percentile(top_factor, [2.5, 97.5])
        top_factor = np.clip(top_factor, lower, upper)
        
        # 分组统计
        res = pd.DataFrame({'factor': top_factor, 'ret': y})
        res['group'] = pd.qcut(res['factor'], 5, labels=['G1', 'G2', 'G3', 'G4', 'G5'])
        group_ret = res.groupby('group')['ret'].mean()
        ic, _ = spearmanr(top_factor, y)
        
        # 绘图
        plt.figure(figsize=(10, 5))
        # 会报warning：sns.barplot(x=group_ret.index, y=group_ret.values, palette='RdYlGn')
        sns.barplot(x=group_ret.index, y=group_ret.values, hue=group_ret.index, palette='RdYlGn', legend=False)
        plt.title(f'Alpha Performance (IC: {ic:.4f})')
        plt.show()
        return ic

    def save_latest_factors(self, df, output_path):
        """生成最新因子 CSV（增加了空值清洗逻辑）"""
        # 1. 确保日期格式正确并排序
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # 2. 只取每只股票最后一天的数据
        latest_df = df.sort_values('date').groupby('stock_code').tail(1).copy()
        
        # 【关键修复】：在预处理前，必须先删掉特征列中有 NaN 的行
        # 否则截面归一化或 transform 都会报错
        before_count = len(latest_df)
        latest_df = latest_df.dropna(subset=self.feature_cols)
        after_count = len(latest_df)
        
        if before_count > after_count:
            print(f"提示：由于特征缺失，跳过了 {before_count - after_count} 只股票。")

        if latest_df.empty:
            print("错误：筛选出的最新数据为空，请检查原始数据。")
            return

        # 3. 预处理（内部会执行截面标准化）
        # 注意：preprocess_data 会返回 X, y, df。由于这里没有 target，我们只取 X
        X, _, _processed_df = self.preprocess_data(latest_df)
        
        # 4. 执行标准化和转换
        X_scaled = self.scaler.transform(X)
        latest_df['factor_value'] = self.gp.transform(X_scaled)[:, 0]
        
        # 5. 格式化并保存
        out = latest_df[['date', 'stock_code', 'factor_value']].copy()
        out['date'] = out['date'].dt.strftime('%Y-%m-%d')
        # 再次确保代码是 6 位字符串
        out['stock_code'] = out['stock_code'].astype(str).str.zfill(6)
        
        # 保存为 CSV (建议使用 utf-8-sig 以便 Excel 查看)
        out.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n因子计算完成!")
        print(f"因子已保存至: {output_path}，共 {len(out)} 条记录。")

    # ========================== 主运行口 ==========================
    def miner_run(self, csv_path, start_date, end_date, output_path):

        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_full_path = os.path.join(script_dir, csv_path)
        output_full_path = os.path.join(script_dir, output_path)

        # 1. 加载数据
        raw_df = process_stocks_from_csv(csv_full_path, start_date, end_date, max_workers=20)
        
        # 2. 初始化并运行
        self.fit(raw_df)
        
        # 3. 回测评价
        self.evaluate(raw_df)
        
        # 4. 保存结果
        self.save_latest_factors(raw_df, output_full_path)



# ==========================================
if __name__ == "__main__":
    FEATURE_COLS = ['ma5_bias', 'ma16_rel', 'ma243_bias', 'ma_spread', 'price_dif_max', 
                    'price_dif', 'macd', 'macd_slope', 'volume_z', 'bb_div', 
                    'bb_width_slope', 'bb_close_div']
    

    # 初始化并运行
    miner = GPAlphaMiner(FEATURE_COLS)
    miner.miner_run(
        csv_path="stock_pool.csv", 
        start_date="2023-01-01", 
        end_date="2024-06-30", 
        output_path="latest_factors.csv"
    )