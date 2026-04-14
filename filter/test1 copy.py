import akshare as ak
import pandas as pd
import time

# 全局配置：轻量延迟，防同花顺限流（几乎不用，同花顺接口很稳）
def setup_akshare():
    print("=== 纯同花顺资金流向盯盘系统启动 ===")

class THSFundAnalysis:
    def __init__(self):
        setup_akshare()

    # ------------------------------
    # 1. 同花顺-90行业资金流（即时）
    # ------------------------------
    def get_industry_fund(self, symbol="即时"):
        """获取90个行业（同花顺分类）资金流"""
        try:
            df = ak.stock_fund_flow_industry(symbol=symbol)
            print(f"✅ 行业资金流({symbol})获取成功 | 共{len(df)}个行业")
            time.sleep(1)
            return df
        except Exception as e:
            print(f"❌ 行业资金流获取失败: {e}")
            return pd.DataFrame()

    # ------------------------------
    # 2. 同花顺-概念资金流（即时）
    # ------------------------------
    def get_concept_fund(self, symbol="即时"):
        """获取概念板块资金流"""
        try:
            df = ak.stock_fund_flow_concept(symbol=symbol)
            print(f"✅ 概念资金流({symbol})获取成功 | 共{len(df)}个概念")
            time.sleep(1)
            return df
        except Exception as e:
            print(f"❌ 概念资金流获取失败: {e}")
            return pd.DataFrame()

    # ------------------------------
    # 3. 同花顺-个股资金流（即时）
    # ------------------------------
    def get_stock_fund(self, symbol="即时"):
        """获取全市场个股资金流排行"""
        try:
            df = ak.stock_fund_flow_individual(symbol=symbol)
            print(f"✅ 个股资金流({symbol})获取成功 | 共{len(df)}只股票")
            time.sleep(1)
            return df
        except Exception as e:
            print(f"❌ 个股资金流获取失败: {e}")
            return pd.DataFrame()

    # ------------------------------
    # 4. 同花顺-大单追踪（实时）
    # ------------------------------
    def get_big_deal(self):
        """获取实时大单成交数据"""
        try:
            df = ak.stock_fund_flow_big_deal()
            print(f"✅ 大单追踪获取成功 | 共{len(df)}条大单记录")
            return df
        except Exception as e:
            print(f"❌ 大单追踪获取失败: {e}")
            return pd.DataFrame()

    # ------------------------------
    # 核心分析：行业资金流向（90行业）
    # ------------------------------
    def analyze_industry(self, df):
        if df.empty:
            print("\n⚠️ 行业数据为空，跳过分析")
            return
        print("\n===== 【90行业资金流向 TOP10】=====")
        # 按净额降序排序
        df_sort = df.sort_values(by="净额", ascending=False)
        # 流入TOP10
        print("\n🔝 资金净流入TOP10行业：")
        for _, row in df_sort.head(10).iterrows():
            print(f"{row['行业']:8} | 净额:{row['净额']:>6.2f}亿 | 涨幅:{row['行业-涨跌幅']:>5} | 领涨:{row['领涨股']}({row['领涨股-涨跌幅']})")
        # 流出TOP10
        print("\n🔻 资金净流出TOP10行业：")
        for _, row in df_sort.tail(10).iterrows():
            print(f"{row['行业']:8} | 净额:{row['净额']:>6.2f}亿 | 涨幅:{row['行业-涨跌幅']:>5} | 领涨:{row['领涨股']}({row['领涨股-涨跌幅']})")

    # ------------------------------
    # 核心分析：概念资金流向
    # ------------------------------
    def analyze_concept(self, df):
        if df.empty:
            print("\n⚠️ 概念数据为空，跳过分析")
            return
        print("\n===== 【概念板块资金流向 TOP10】=====")
        df_sort = df.sort_values(by="净额", ascending=False)
        print("\n🔥 热门概念净流入TOP10：")
        for _, row in df_sort.head(10).iterrows():
            print(f"{row['行业']:12} | 净额:{row['净额']:>5.2f}亿 | 涨幅:{row['行业-涨跌幅']:>4.2f}% | 领涨:{row['领涨股']}({row['领涨股-涨跌幅']:.2f}%)")

    # ------------------------------
    # 核心分析：个股资金流排行
    # ------------------------------
    def analyze_stock(self, df):
        if df.empty:
            print("\n⚠️ 个股数据为空，跳过分析")
            return
        print("\n===== 【个股资金净流入 TOP20】=====")
        df_sort = df.sort_values(by="净额", ascending=False)
        for _, row in df_sort.head(20).iterrows():
            print(f"{row['股票简称']:6}({row['股票代码']}) | 净额:{row['净额']:>8} | 涨幅:{row['涨跌幅']:>5} | 最新价:{row['最新价']:.2f} | 成交额:{row['成交额']}")

    # ------------------------------
    # 核心分析：实时大单追踪
    # ------------------------------
    def analyze_big_deal(self, df):
        if df.empty:
            print("\n⚠️ 大单数据为空，跳过分析")
            return
        print("\n===== 【实时大单追踪 TOP20】=====")
        # 按成交额降序
        df_sort = df.sort_values(by="成交额", ascending=False)
        for _, row in df_sort.head(20).iterrows():
            print(f"{row['成交时间']} | {row['股票简称']:6} | 价格:{row['成交价格']:.2f} | 成交额:{row['成交额']:>6.2f}万 | 性质:{row['大单性质']} | 涨跌幅:{row['涨跌幅']}")

    # ------------------------------
    # 一键运行：全同花顺资金分析
    # ------------------------------
    def run(self, period="即时"):
        # 1. 获取数据（纯同花顺，无东方财富）
        industry_df = self.get_industry_fund(period)
        concept_df = self.get_concept_fund(period)
        stock_df = self.get_stock_fund(period)
        big_deal_df = self.get_big_deal()

        # 2. 执行分析
        self.analyze_industry(industry_df)
        self.analyze_concept(concept_df)
        self.analyze_stock(stock_df)
        self.analyze_big_deal(big_deal_df)

        print("\n✅ 纯同花顺资金流向分析完成！")

if __name__ == "__main__":
    # 实例化并运行（period可选：即时/3日排行/5日排行/10日排行/20日排行）
    ths_analysis = THSFundAnalysis()
    ths_analysis.run(period="即时")