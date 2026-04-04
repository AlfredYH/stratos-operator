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
from pywinauto import Application, keyboard
from loguru import logger
import time
from .reg import ocr_trade_info_bytes
from .reg import ocr_trade_info_popup
from . import start_ht
from . import get_position
from . import get_popup_window


class TradeOperator:
    def __init__(self, app_title="网上股票交易系统5.0"):
        self.app_title = app_title

        try:
            self.app = Application(backend="win32").connect(title_re=self.app_title)
            self.main_win = self.app.window(title_re=self.app_title)
            print(f"程序已经打开，成功连接到应用 '{self.app_title}'")
            logger.success(f"成功连接到应用 '{self.app_title}'")
            

        except Exception:
            print(f"❌ 未找到应用 '{self.app_title}'，正在启动...")
            logger.warning(f"未找到应用 '{self.app_title}'，正在启动...")
            start_ht.start()
            self.app = Application(backend="win32").connect(title_re=self.app_title)
            self.main_win = self.app.window(title_re=self.app_title)
            print(f"✅ 成功连接到应用 '{self.app_title}'")
            logger.success(f"成功连接到应用 '{self.app_title}'")


    def _get_origin_point_coordinate(self):
        # 后面所有的定位都尽量使用Tree结构右上角作为origin point

        main_win = self.main_win
        main_win.set_focus()

        ctrl = self.main_win.child_window(class_name="SysTreeView32")
        rect = ctrl.rectangle()
        # 保存区域信息用于后续坐标还原
        area_info = {
            "left": rect.left, "top": rect.top,
            "width": rect.width(), "height": rect.height()
        }

        # 这里计算的是tree结果的右上角坐标，更加健壮
        origin_point_coodinate = (area_info["left"] + area_info["width"],
                                  area_info["top"])
        
        return origin_point_coodinate


    def buy_in(self, stock_code: str, quantity: int):
        # 注意，此时价格还不知道，可能需要先获取当前价格或者使用预设价格
        if quantity <= 0 or quantity % 100 != 0:
            raise ValueError(f"买入数量非法：{quantity}，必须是100的倍数且大于0")
        
        print(f"正在执行买入: 股票代码={stock_code},  数量={quantity}")
        logger.info(f"正在执行买入: 股票代码={stock_code},  数量={quantity}")

        main_win = self.main_win
        main_win.set_focus()

        keyboard.send_keys("{F1}")  # 打开买入界面
        time.sleep(0.2)  # 等待界面打开
        keyboard.send_keys(stock_code)  # 输入股票代码
        time.sleep(0.8)
        keyboard.send_keys("{TAB}")
        time.sleep(0.2)
        keyboard.send_keys("{TAB}")
        time.sleep(0.2)
        keyboard.send_keys(str(quantity))  # 输入买入数量
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.2)

        print("正在处理委托确认弹窗...")
        img_bytes = get_popup_window.capture_popup_window()
        buy_in_info = ocr_trade_info_popup.ocr_buy_in_confirmation(img_bytes)
        
        keyboard.send_keys("{ENTER}")  # 委托确认
        time.sleep(0.1)

        print("正在处理委托确认后的提示弹窗...")
        # 处理可能出现的弹窗
        buy_in_result = get_popup_window.trade_hint_popup_window_analysis()
        # print(f"弹窗处理结果: {buy_in_result}")

        keyboard.send_keys("{ENTER}")  # 确认弹窗
        time.sleep(0.1)

        if buy_in_result["status"] == "success":
            print("买入委托成功")
            logger.success(f"买入委托成功: 股票代码={stock_code},\
                           买入价格={buy_in_info['Price']},\
                            数量={quantity}")
            return buy_in_info
        
        else:
            print("买入委托失败", buy_in_result.get("message", "未知错误"))
            logger.error(f"买入委托失败: 股票代码={stock_code},\
                         错误信息: {buy_in_result.get('message', '未知错误')}")
            return None



    def sell_out(self, stock_code: str, quantity: int):
        # 注意，此时价格还不知道，可能需要先获取当前价格或者使用预设价格
        if quantity <= 0 or quantity % 100 != 0:
            raise ValueError(f"卖出数量非法：{quantity}，必须是100的倍数且大于0")
        
        print(f"正在执行卖出: 股票代码={stock_code},  数量={quantity}")
        logger.info(f"正在执行卖出: 股票代码={stock_code},  数量={quantity}")

        main_win = self.main_win
        main_win.set_focus()

        keyboard.send_keys("{F2}")  # 打开卖出界面
        time.sleep(0.2)  # 等待界面打开
        keyboard.send_keys(stock_code)  # 输入股票代码
        time.sleep(0.8)
        keyboard.send_keys("{TAB}")
        time.sleep(0.2)
        keyboard.send_keys("{TAB}")
        time.sleep(0.2)
        keyboard.send_keys(str(quantity))  # 输入卖出数量
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.2)

        print("正在处理委托确认弹窗...")
        img_bytes = get_popup_window.capture_popup_window()
        sell_out_info = ocr_trade_info_popup.ocr_sell_out_confirmation(img_bytes)
        
        keyboard.send_keys("{ENTER}")  # 委托确认
        time.sleep(0.1)

        print("正在处理委托确认后的提示弹窗...")
        # 处理可能出现的弹窗
        sell_out_result = get_popup_window.trade_hint_popup_window_analysis()
        # print(f"弹窗处理结果: {sell_out_result}")

        keyboard.send_keys("{ENTER}")  # 确认弹窗
        time.sleep(0.1)

        if sell_out_result["status"] == "success":
            print("卖出委托成功")
            logger.success(f"卖出委托成功: 股票代码={stock_code},\
                           卖出价格={sell_out_info['Price']},\
                            数量={quantity}")
            return sell_out_info
        
        else:
            print("卖出委托失败", sell_out_result.get("message", "未知错误"))
            logger.error(f"卖出委托失败: 股票代码={stock_code},\
                         错误信息: {sell_out_result.get('message', '未知错误')}")
            return None



    def get_position_info(self):
        print("正在获取持仓信息...")
        df = get_position.get_position()
        return df
    
    


    # 如果使用委托确认弹窗来获取交易信息，这个模块就弃用
    def get_trade_info(self) -> dict:

        # 注意！！！！！！
        # 如果使用委托确认弹窗来获取交易信息，这个模块就弃用

        print("正在获取交易信息...")
        
        origin_point_coodinate = self._get_origin_point_coordinate()
        
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

        # with mss.mss() as sct:
        #     sct_img = sct.grab(trade_info_area)
        #     # 保存为本地文件供 Ollama 读取
        #     # mss.tools.to_png(sct_img.rgb, sct_img.size, output="screenshot.png")
        #     mss.tools.to_png(sct_img.rgb, sct_img.size, output="screenshot.png")


if __name__ == "__main__":
    from reg import ocr_trade_info_bytes
    trader = TradeOperator()
    info = trader.get_trade_info_debug()
    
    print("获取交易信息完成")

    print(info)

            
