import ollama
import re
import socket  # 导入 socket 库

def is_ollama_running(host='localhost', port=11434):
    """检测指定端口是否开放"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)  # 设置 1 秒超时，避免阻塞太久
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

def call_ollama_ocr(image_data_bytes):
    # 配置
    OLLAMA_HOST_NAME = 'localhost'
    OLLAMA_PORT = 11434
    OLLAMA_HOST = f'http://{OLLAMA_HOST_NAME}:{OLLAMA_PORT}'
    MODEL_NAME = 'deepseek-ocr:3b'

    # --- 新增检测逻辑 ---
    if not is_ollama_running(OLLAMA_HOST_NAME, OLLAMA_PORT):
        return None, f"❌ 错误: 无法连接到 Ollama 服务。请确保已启动 Ollama 并在端口 {OLLAMA_PORT} 监听。"
    # ------------------

    client = ollama.Client(host=OLLAMA_HOST)
    
    prompt = "OCR recognizes the four Arabic digits verification code " \
             "in this image and outputs only the four digits."

    try:
        response = client.chat(
            model=MODEL_NAME,
            keep_alive='5m',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data_bytes]
            }]
        )
        
        raw_content = response['message']['content'].strip()
        all_digits = re.findall(r'\d', raw_content)
        final_value = "".join(all_digits[:4]) if len(all_digits) >= 4 else "not found"

        return final_value, None

    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    import os
    IMAGE_PATH = os.path.join(os.path.dirname(__file__), "test_captcha.png")
    
    try:
        with open(IMAGE_PATH, 'rb') as f:
            img_bytes = f.read()
            result, error = call_ollama_ocr(img_bytes)
    except FileNotFoundError:
        result, error = None, "图片文件未找到"
    
    if result and result != "not found":
        print("✅ OCR 识别成功：")
        print(result)
    else:
        print(f"{error if error else '❌ 识别失败: 未提取到数字'}")