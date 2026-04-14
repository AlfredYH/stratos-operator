from quant.miner import GPAlphaMiner

if __name__ == "__main__":
    print("🚀 因子挖掘系统启动")
    miner = GPAlphaMiner()
    miner.miner_run(
        start_date="2023-01-01",
        end_date="2024-06-30"
    )