import requests
import base64
import re

def ocr_trade_info_to_json(base64_str: str) -> dict:
    """
    针对 DeepSeek-OCR 原生 HTML Table 输出的解析版
    """
    # 官方 Prompt
    prompt = "<image>\n<|grounding|>Convert the document to markdown."
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": "deepseek-ocr:3b",
        "messages": [{"role": "user", "content": prompt, "images": [base64_str]}],
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "keep_alive": 0  # 建议添加，防止 500 错误
        }
    }

    # 预定义的空字典
    info = {
        "StockCode": "",
        "StockName": "",
        "Price": "",
        "AvailableShares": "",
        "OrderQuantity": ""
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        # 拿到包含 <table>...</table> 的原始文本
        raw_content = result["message"]["content"]

        # -------------------------------------------------------
        # 核心修改：使用正则提取所有 <td> 标签中的内容
        # -------------------------------------------------------
        # re.findall 会抓取 <td> 和 </td> 之间的所有字符
        cells = re.findall(r'<td>(.*?)</td>', raw_content)

        # cells 现在是一个列表，例如: ['证券代码', '600010', '证券名称', '包钢股份', ...]
        # 我们每隔两个元素取一次，形成键值对
        if len(cells) >= 2:
            # zip(cells[0::2], cells[1::2]) 会将 ['键1', '值1', '键2', '值2'] 变成 [('键1', '值1'), ...]
            raw_dict = dict(zip(cells[0::2], cells[1::2]))
            
            # 定义映射关系，确保无论模型输出什么中文标签，都能对接到你的 info 字典
            mapping = {
                "证券代码": "StockCode",
                "证券名称": "StockName",
                "买入价格": "Price",
                "卖出价格": "Price",
                "价格": "Price",
                "可买（股）": "AvailableShares",
                "可卖（股）": "AvailableShares",
                "买入数量": "OrderQuantity",
                "卖出数量": "OrderQuantity"
            }

            # 填充 info 字典
            for k, v in raw_dict.items():
                clean_key = k.strip()
                if clean_key in mapping:
                    # 再次清理值（剔除可能的光标符号 | 等）
                    clean_value = re.sub(r'[\|lI]$', '', v.strip())
                    info[mapping[clean_key]] = clean_value

        return info

    except Exception as e:
        print(f"调用失败: {e}")
        return info

# ------------------------------
# 测试入口
# ------------------------------
if __name__ == "__main__":
    with open("screenshot.png", "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    result = ocr_trade_info_to_json(base64_image)
    print("✅ 最终返回字典：")
    print(result)