"""
新版本使用买入或者买入后的确认弹窗来进行OCR识别，避免了之前直接在主界面进行OCR识别的复杂性和不稳定性。
"""


import requests
import base64
import re
from loguru import logger


def ocr_buy_in_confirmation(img_bytes: bytes) -> dict:
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "deepseek-ocr:3b",
        "messages": [{"role": "user",
                      "content": "<image>\nConvert the image to markdown text.",
                      "images": [base64.b64encode(img_bytes).decode('utf-8')]}],
        "stream": False,
        "options": {"temperature": 0}
    }

    # 预定义返回字典（初始值为 None，方便判断是否识别失败）
    trade_info = {
        "StockCode": None,    # 应为 str
        "Price": 0.0,         # 应为 float
        "Quantity": 0,        # 应为 int
        "TotalAmount": 0.0    # 应为 float
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        raw_text = response.json()["message"]["content"]
        
        # 1. 匹配原始字符串
        patterns = {
            "StockCode": r"证券代码[:：]\s*(\d+)",
            "Price": r"买入价格[:：]\s*([\d\.]+)",
            "Quantity": r"买入数量[:：]\s*(\d+)",
            "TotalAmount": r"预估金额[:：]\s*([\d\.]+)"
        }

        # 2. 提取并强制类型转换
        for key, reg in patterns.items():
            match = re.search(reg, raw_text)
            if match:
                val = match.group(1)
                try:
                    if key == "StockCode":
                        trade_info[key] = str(val)      # 保持字符串，保留开头的0
                    elif key == "Quantity":
                        trade_info[key] = int(val)      # 转为整数
                    else:
                        trade_info[key] = float(val)    # Price 和 TotalAmount 转为浮点
                except ValueError:
                    logger.error(f"字段 {key} 转换失败，原始值: {val}")

        # 3. 业务逻辑二次校验 (Double Check)
        if trade_info["Quantity"] % 100 != 0:
            logger.warning(f"注意：识别到的数量 {trade_info['Quantity']} 不是100的倍数，请核实！")

        logger.success(f"解析完成: {trade_info}")
        return trade_info

    except Exception as e:
        logger.exception("OCR 流程异常")
        return trade_info


def ocr_sell_out_confirmation(img_bytes: bytes) -> dict:
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "deepseek-ocr:3b",
        "messages": [{"role": "user",
                      "content": "<image>\nConvert the image to markdown text.",
                      "images": [base64.b64encode(img_bytes).decode('utf-8')]}],
        "stream": False,
        "options": {"temperature": 0}
    }

    # 预定义返回字典（初始值为 None，方便判断是否识别失败）
    trade_info = {
        "StockCode": None,    # 应为 str
        "Price": 0.0,         # 应为 float
        "Quantity": 0,        # 应为 int
        "TotalAmount": 0.0    # 应为 float
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        raw_text = response.json()["message"]["content"]
        
        # 1. 匹配原始字符串
        patterns = {
            "StockCode": r"证券代码[:：]\s*(\d+)",
            "Price": r"卖出价格[:：]\s*([\d\.]+)",
            "Quantity": r"卖出数量[:：]\s*(\d+)",
            "TotalAmount": r"预估金额[:：]\s*([\d\.]+)"
        }

        # 2. 提取并强制类型转换
        for key, reg in patterns.items():
            match = re.search(reg, raw_text)
            if match:
                val = match.group(1)
                try:
                    if key == "StockCode":
                        trade_info[key] = str(val)      # 保持字符串，保留开头的0
                    elif key == "Quantity":
                        trade_info[key] = int(val)      # 转为整数
                    else:
                        trade_info[key] = float(val)    # Price 和 TotalAmount 转为浮点
                except ValueError:
                    logger.error(f"字段 {key} 转换失败，原始值: {val}")

        # 3. 业务逻辑二次校验 (Double Check)
        if trade_info["Quantity"] % 100 != 0:
            logger.warning(f"注意：识别到的数量 {trade_info['Quantity']} 不是100的倍数，请核实！")

        logger.success(f"解析完成: {trade_info}")
        return trade_info

    except Exception as e:
        logger.exception("OCR 流程异常")
        return trade_info







# --- 测试运行 ---
if __name__ == "__main__":
    # 读取你上传的那张截图
    with open("test_buyin_confirm.png", "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    result = ocr_buy_in_confirmation(img_base64)
    print("\n--- 最终交易字典 ---")
    print(result)

    with open("test_sell_out_confirm.png", "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    result = ocr_sell_out_confirmation(img_base64)
    print("\n--- 最终交易字典 ---")
    print(result)