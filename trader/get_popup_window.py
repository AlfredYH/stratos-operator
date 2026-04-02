import os
import sys

os.environ['PYTHONWARNINGS'] = 'ignore:32-bit application:UserWarning'

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pywinauto.application')

import cv2
import numpy as np
import json
import mss
from pywinauto import Desktop
from .reg import ocr_popup_buysell_bytes


def capture_popup_window(class_name="#32770", index=0):
    """
    定位窗口，截图，转换为灰度，并返回二进制字节流
    """
    des = Desktop(backend="win32")
    try:
        dlg_find = des.window(class_name=class_name, found_index=index)
        dlg_find.set_focus()
        rect = dlg_find.rectangle()
    except Exception as e:
        print(f"未找到窗口: {e}")
        return None

    with mss.mss() as sct:
        monitor = {
            "top": rect.top,
            "left": rect.left,
            "width": rect.width(),
            "height": rect.height()
        }
        sct_img = sct.grab(monitor)
        img = np.array(sct_img)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

    success, img_bin = cv2.imencode('.png', img_gray)
    
    if success:
        return img_bin.tobytes()
    return None


def get_popup_window(class_name="#32770", index=0):
    """
    捕获弹窗窗口，进行OCR识别并返回JSON分析结果
    """
    img_bytes = capture_popup_window(class_name, index)
    if not img_bytes:
        return {"error": "截图失败"}
    
    analyzer = ocr_popup_buysell_bytes.PopupAnalyzer()
    return analyzer.analyze_popup_from_image(img_bytes)


if __name__ == "__main__":
    result = get_popup_window()
    print(json.dumps(result, ensure_ascii=False, indent=2))
