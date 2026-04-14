import pandas as pd
import numpy as np
import yaml
import loguru

from trader.trader import TradeOperator


CONFIG_PATH = "config.yaml"

class Stratos():
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def process(self):
        # Example processing: Calculate the mean of each column
        return self.data.mean()
    

class StratosOperator():
    def __init__(self, stratos: Stratos, trader_number: int = 1):
        self.stratos = stratos
        self.trader_number = trader_number

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            trader_name = f"Trader{self.trader_number}"
            self.config = config[trader_name]
        self.mode = self.config["mode"]
        """待补充完整参数"""





    def _get_stock_fac_data(self, df: pd.DataFrame):
        # 获取股票因子df
        # 校验包含必要的列
        return df

    def _position_analyzing(self):
        # Position analysing
        ope = TradeOperator()
        position_info = ope.get_position_info()

    def _order_analyzing(self) -> dict:
        # 满足T+1的订单分析
        # 返回股票代码和最大允许卖出数量的字典
        return {}

    def _trade_decision(self) -> pd.DataFrame:
        # 注意，要根据因子比例决定资金分配






        # 根据分析结果做出交易决策
        # 返回买入/卖出信号和数量
        df = pd.DataFrame()  # 示例返回空DataFrame，实际应包含交易决策
        df_buy = df[df['action'] == 'buy']
        df_sell = df[df['action'] == 'sell']
        return df_buy, df_sell
    
    def execute(self):
        trader = TradeOperator()
        decision_df_buy, decision_df_sell = self._trade_decision()
        for index, row in decision_df_sell.iterrows():
            try:
                trader.sell_out(row['stock_code'], row['quantity'])
                loguru.logger.info(f"Successfully sold {row['quantity']} of {row['stock_code']}")
            except Exception as e:
                print(f"Error occurred while selling {row['stock_code']}: {e}")
                loguru.logger.error(f"Error occurred while selling {row['stock_code']}: {e}")
        for index, row in decision_df_buy.iterrows():
            try:
                trader.buy_in(row['stock_code'], row['quantity'])
                loguru.logger.info(f"Successfully bought {row['quantity']} of {row['stock_code']}")
            except Exception as e:
                print(f"Error occurred while buying {row['stock_code']}: {e}")
                loguru.logger.error(f"Error occurred while buying {row['stock_code']}: {e}")

