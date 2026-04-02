import json
import re
import base64
import socket
import requests
import yaml


def is_ollama_running(host='localhost', port=11434):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False


def call_ollama_ocr(image_bytes, model="deepseek-ocr:3b", host="http://localhost:11434"):
    if not is_ollama_running():
        return None, "无法连接到Ollama服务"

    api_url = f"{host}/api/generate"
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = "<image>\nFree OCR."
    prompt = "<image>\n<|grounding|>Convert the document to markdown."

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False
    }

    try:
        response = requests.post(api_url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        response_text = result.get("response", "")
        print(f"OCR原始响应内容: {response_text[:500]}")
        return response_text, None
    except Exception as e:
        return None, str(e)


class PopupAnalyzer:
    def __init__(self, model="qwen3.5:4b", host="http://localhost:11434"):
        self.model = model
        self.api_url = f"{host}/api/generate"
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        import os
        yaml_path = os.path.join(os.path.dirname(__file__), "prompt_buysell.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def analyze_popup(self, raw_text):
        prompt_cfg = self.prompts["popup_window_analyze"]
        
        user_template = prompt_cfg['user'].replace('{{ ocr_text }}', raw_text)
        full_prompt = f"{prompt_cfg['system']}\n\n{user_template}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
            "temperature": 0,
            "options": {
                "num_ctx": 512
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "") or result.get("thinking", "")
            if not response_text:
                return {"error": "Empty response from model"}
            return self._parse_json_response(response_text)
        except Exception as e:
            return {"error": str(e)}

    def _parse_json_response(self, response_text):
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return {"error": "Failed to parse JSON", "raw": response_text}

    def analyze_popup_from_image(self, image_bytes):
        ocr_text, error = call_ollama_ocr(image_bytes, self.model)
        if error:
            return {"error": error}
        
        if not ocr_text or not ocr_text.strip():
            return {"error": "OCR识别结果为空"}
        
        return self.analyze_popup(ocr_text)


if __name__ == "__main__":
    import os
    print("--- OCR弹窗分析测试 ---")
    
    IMAGE_PATH = os.path.join(os.path.dirname(__file__), "testbuysell.png")
    
    try:
        with open(IMAGE_PATH, 'rb') as f:
            img_bytes = f.read()
            print(f"[OK] 已读取图片: {IMAGE_PATH}, 大小: {len(img_bytes)} 字节")
    except FileNotFoundError:
        print(f"图片文件未找到: {IMAGE_PATH}")
        exit(1)
    
    analyzer = PopupAnalyzer(model="qwen3.5:4b")
    
    result = analyzer.analyze_popup_from_image(img_bytes)
    
    print("\n最终JSON结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))
