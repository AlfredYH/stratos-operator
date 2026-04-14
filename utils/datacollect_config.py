import os
import yaml
from typing import Any, Optional


class Config(object):
    _instance: Optional['Config'] = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "datacollect_config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def tushare_token(self) -> str:
        return self.get("client.TUSHARE_TOKEN", "")

    @property
    def debug_mode(self) -> bool:
        return self.get("data_collect.debug_mode", False)

    @property
    def start_date(self) -> str:
        return self.get("data_collect.start_date", "2014-01-01")

    @property
    def end_date(self) -> str:
        return self.get("data_collect.end_date", "")

    @property
    def frequency(self) -> str:
        return self.get("data_collect.frequency", "daily")

    @property
    def stock_list_source(self) -> str:
        return self.get("data_collect.stock_list_source", "tushare")

    @property
    def stock_history_source(self) -> str:
        return self.get("data_collect.stock_history_source", "akshare")

    @property
    def adjust_type_qfq(self) -> str:
        return self.get("data_collect.adjust_type_qfq", "qfq")

    @property
    def adjust_type_hfq(self) -> str:
        return self.get("data_collect.adjust_type_hfq", "hfq")

    @property
    def adjust_type_bfq(self) -> str:
        return self.get("data_collect.adjust_type_bfq", "bfq")

    @property
    def db_name(self) -> str:
        return self.get("daily_update.db_name", "stockdata.db")

    @property
    def list_name(self) -> str:
        return self.get("daily_update.list_name", "stock_list.parquet")

    @property
    def max_workers(self) -> int:
        return self.get("daily_update.max_workers", 4)

    @property
    def batch_commit(self) -> int:
        return self.get("daily_update.batch_commit", 100)


def get_config() -> Config:
    return Config()