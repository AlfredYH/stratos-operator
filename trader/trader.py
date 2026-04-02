import re
import os
import cv2
import numpy as np
from flask import app
import mss
import io
import base64
from PIL import Image
from datetime import datetime, time
from pywinauto import Application
from .reg import ocr_trade_info_bytes
from . import start_ht
from . import get_position
from . import get_popup_window

class TradeOperator:
    def __init__(self, app_title="网上股票交易系统5.0", class_name="SysTreeView32"):
        self.app_title = app_title
        self.class_name = class_name
        
        try:
            self.app = Application(backend="win32").connect(title_re=self.app_title)
            self.main_win = self.app.window(title_re=self.app_title)
            print(f"程序已经打开，成功连接到应用 '{self.app_title}'")
            

        except Exception:
            print(f"❌ 未找到应用 '{self.app_title}'，正在启动...")
            start_ht.start()
            self.app = Application(backend="win32").connect(title_re=self.app_title)
            self.main_win = self.app.window(title_re=self.app_title)
            print(f"✅ 成功连接到应用 '{self.app_title}'")


    def buy_in(self, stock_code, price, quantity):
        # 注意，此时价格还不知道，可能需要先获取当前价格或者使用预设价格
        print(f"正在执行买入操作: 股票代码={stock_code}, 价格={price}, 数量={quantity}")
        main_win = self.main_win
        main_win.set_focus()


    def sell_out(self, stock_code, price, quantity):
        # 注意，此时价格还不知道，可能需要先获取当前价格或者使用预设价格
        print(f"正在执行卖出操作: 股票代码={stock_code}, 价格={price}, 数量={quantity}")
        main_win = self.main_win
        main_win.set_focus()


    def get_position_info(self):
        print("正在获取持仓信息...")
        df = get_position.get_position()
        return df
    

    def popup_handle(self):
        print("正在处理弹窗...")
        result = get_popup_window()
        # Logger.info(f"弹窗处理结果: {result}")
        return result
    

    def get_trade_info(self) -> dict:
        print("正在获取交易信息...")
        main_win = self.main_win
        main_win.set_focus()
        ctrl = main_win.child_window(class_name=self.class_name)
        rect = ctrl.rectangle()
        # 保存区域信息用于后续坐标还原
        area_info = {
            "left": rect.left, "top": rect.top,
            "width": rect.width(), "height": rect.height()
        }

        # 注意这里计算的是tree结果的右上角坐标，更加健壮
        origin_point_coodinate = (area_info["left"] + area_info["width"],
                                  area_info["top"])
        
        # 这里将买入卖出部分的图片截取出来，方便后续处理，适配股票界面
        trade_info_area = {
            "left": origin_point_coodinate[0] + 40,
            "top": origin_point_coodinate[1] + 54,
            "width": 191,
            "height": 145
        }
        
        with mss.mss() as sct:
            sct_img = sct.grab(trade_info_area)

            # mss.tools.to_png(sct_img.rgb, sct_img.size, output="screenshot.png")
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")

            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            trade_info = ocr_trade_info_bytes.ocr_trade_info_to_json(img_base64)

            return trade_info
        
    def get_trade_info_debug(self) -> dict:
        print("正在获取交易信息...")
        main_win = self.main_win
        main_win.set_focus()
        ctrl = main_win.child_window(class_name=self.class_name)
        rect = ctrl.rectangle()
        # 保存区域信息用于后续坐标还原
        area_info = {
            "left": rect.left, "top": rect.top,
            "width": rect.width(), "height": rect.height()
        }

        # 注意这里计算的是tree结果的右上角坐标，更加健壮
        origin_point_coodinate = (area_info["left"] + area_info["width"],
                                  area_info["top"])
        
        # 这里将买入卖出部分的图片截取出来，方便后续处理，适配股票界面
        trade_info_area = {
            "left": origin_point_coodinate[0] + 40,
            "top": origin_point_coodinate[1] + 54,
            "width": 191,
            "height": 145
        }

        with mss.mss() as sct:
            sct_img = sct.grab(trade_info_area)
            # 保存为本地文件供 Ollama 读取
            # mss.tools.to_png(sct_img.rgb, sct_img.size, output="screenshot.png")
            mss.tools.to_png(sct_img.rgb, sct_img.size, output="screenshot.png")


if __name__ == "__main__":
    from reg import ocr_trade_info_bytes
    trader = TradeOperator()
    info = trader.get_trade_info_debug()
    
    print("获取交易信息完成")

    print(info)

            
