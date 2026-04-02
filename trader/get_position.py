import os
import sys

# 关键：在所有导入之前，强制设置环境变量屏蔽该警告
os.environ['PYTHONWARNINGS'] = 'ignore:32-bit application:UserWarning'

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pywinauto.application')


import cv2
import numpy as np
import pandas as pd
import io
import mss
from pywinauto import Application, Desktop, keyboard
import time
from datetime import datetime
import pyperclip
from .reg import ocr_captcha_bytes



def capture_captcha_window(class_name="#32770", index=0):
    """
    定位窗口，截图，转换为灰度，并返回二进制字节流
    """
    # 1. 定位窗口
    des = Desktop(backend="win32")
    try:
        dlg_find = des.window(class_name=class_name, found_index=index)
        dlg_find.set_focus()
        rect = dlg_find.rectangle()
    except Exception as e:
        print(f"❌ 未找到窗口: {e}")
        return None

    # 2. 截图 (mss 速度极快)
    with mss.mss() as sct:
        monitor = {
            "top": rect.top, 
            "left": rect.left, 
            "width": rect.width(), 
            "height": rect.height()
        }
        sct_img = sct.grab(monitor)
        
        # 将 mss 的图像转换为 OpenCV 格式 (BGR)
        # sct_img.rgb 得到的是原始像素数据
        img = np.array(sct_img)
        # 注意：mss grab 出来的是 BGRA 格式，转换为灰度
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

    # 3. 编码为 PNG 二进制流
    # 这里不需要保存到本地再 cv2.imread，直接内存操作
    success, img_bin = cv2.imencode('.png', img_gray)
    
    if success:
        return img_bin.tobytes()
    return None


def get_position() -> pd.DataFrame:

    max_retries=10
    APP_TITLE = "网上股票交易系统5.0"
    app = Application(backend="win32").connect(title_re=APP_TITLE)
    main_win = app.window(title_re=APP_TITLE)
    main_win.set_focus()
    keyboard.send_keys('F4')
    
    for attempt in range(max_retries):

        pyperclip.copy('')
        time.sleep(0.1)
        keyboard.send_keys('^c')
        time.sleep(0.3)
        result = None

        captcha_img_data = capture_captcha_window()

        if not captcha_img_data:
            print(f"❌ 第 {attempt + 1} 次截图失败，重试中...")
            keyboard.send_keys('{ESC}')
            time.sleep(0.3)
            keyboard.send_keys('^c')
            time.sleep(0.3)
            continue


        result, error = ocr_captcha_bytes.call_ollama_ocr(captcha_img_data)
        if result == None or result == "not found":
            print(f"❌ 第 {attempt + 1} 次 OCR 识别失败: {error}，重试中...")
            keyboard.send_keys('{ESC}')
            time.sleep(0.3)
            keyboard.send_keys('^c')
            time.sleep(0.3)
            continue
        
        keyboard.send_keys(result)
        keyboard.send_keys('{ENTER}')
        time.sleep(0.3)
        
        raw_data = pyperclip.paste()

        if raw_data is None or raw_data.strip() == "":
            print(f"❌ 第 {attempt + 1} 次验证码输入错误，重试中...")
            keyboard.send_keys('{ESC}')
            time.sleep(0.3)
            continue

        try:
            df = pd.read_csv(io.StringIO(raw_data.strip()), sep='\t', dtype={'证券代码': str})
            if df is not None and not df.empty:
                return df
        except:
            pass
        
        
    
    print("❌ 已达到最大重试次数")
    return None


# --- 调用示例 ---
# image_data = capture_window_as_gray_bytes()
# if image_data:
#     # 传给你的 Ollama OCR 函数
#     # response = call_ollama_ocr(image_data)
#     print(f"✅ 已获取灰度图片二进制流，大小: {len(image_data)} 字节")

if __name__ == "__main__":
    df = get_position()
    print(df)