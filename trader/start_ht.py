
import warnings

# 改用字符串通配匹配（* 匹配任意字符），兼容所有Python版本
warnings.filterwarnings('ignore', message='.*32-bit application.*')

from pywinauto import Application
from pywinauto.mouse import click
from pywinauto.keyboard import send_keys
from pywinauto import Desktop

import pyautogui
import yaml
import os
import time
import ctypes

# ===================== 核心配置 ======================
EXE_PATH = r"C:\htzqzyb2\hexin.exe"
# Toolbar右上角为原点的偏移量
TOOLBAR_CLICK_OFFSET_X = -187
TOOLBAR_CLICK_OFFSET_Y = 21

# 各个组件相对于dlg的偏移
USER_INPUT_OFFSET_X = 531
USER_INPUT_OFFSET_Y = 104
PWD_INPUT_OFFSET_X = 534
PWD_INPUT_OFFSET_Y = 160
LOGIN_CLICK_OFFSET_X = 445
LOGIN_CLICK_OFFSET_Y = 422

# 配置文件路径（同路径）
CONFIG_PATH = "client.yaml"
# =====================================================

def start():
    warnings.filterwarnings('ignore', message='.*32-bit application.*')
    try:
        username, password = load_plain_config()
        app, main_win = start_hexin_app()
        toolbar_origin = get_toolbar_right_top_coords(main_win)
        if toolbar_origin:
            click_and_input_by_offset(app, main_win, toolbar_origin, username, password)
    except Exception as e:
        print(f"错误: {e}")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def load_plain_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_full_path = os.path.join(script_dir, CONFIG_PATH)

    if not os.path.exists(config_full_path):
        raise FileNotFoundError(f"配置文件不存在: {config_full_path}")

    with open(config_full_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    username = config["client"]["username"]
    password = config["client"]["password"]
    return username, password

def start_hexin_app():
    if not os.path.exists(EXE_PATH):
        raise FileNotFoundError(f"程序不存在: {EXE_PATH}")

    if not is_admin():
        # print("⚠️  建议管理员运行，否则可能控制无效")
        pass

    app = Application(backend="win32").start(EXE_PATH)
    time.sleep(7)

    try:
        main_win = app.window(title_re=".*行情.*")
        main_win.wait('visible', timeout=15)
        main_win.set_focus()
    except:
        main_win = app.top_window()
        main_win.set_focus()
    return app, main_win

def get_toolbar_right_top_coords(main_win):
    toolbar_ctrls = []
    def recursive_find_toolbar(ctrl):
        try:
            if ctrl.class_name() == "ToolbarWindow32":
                toolbar_ctrls.append(ctrl)
            for child in ctrl.children():
                recursive_find_toolbar(child)
        except:
            pass
    recursive_find_toolbar(main_win)

    if not toolbar_ctrls:
        return None

    toolbar_rightmost = None
    max_right_x = 0
    for tb in toolbar_ctrls:
        try:
            rect = tb.rectangle()
            right_x = rect.left + rect.width()
            if right_x > max_right_x:
                max_right_x = right_x
                toolbar_rightmost = tb
        except:
            pass
    if not toolbar_rightmost:
        return None

    r = toolbar_rightmost.rectangle()
    return (r.left + r.width(), r.top)

def click_and_input_by_offset(app, main_win, toolbar_origin, username, password):
    tx, ty = toolbar_origin

    # 打开登录
    tgt_x = tx + TOOLBAR_CLICK_OFFSET_X
    tgt_y = ty + TOOLBAR_CLICK_OFFSET_Y
    main_win.set_focus()
    time.sleep(3)
    click(coords=(tgt_x, tgt_y))
    time.sleep(3)

    # 客户号
    try:
        dlg_login = app.window(class_name="#32770", found_index=0)
        if dlg_login.exists():
            rect = dlg_login.rectangle()
            # 执行点击逻辑...
            # print(f"找到窗口，坐标：{rect}")

            # 提取右上角坐标
            # rect.right 是窗口最右侧的横坐标
            # rect.top 是窗口最顶部的纵坐标
            base1_x = rect.left
            base1_y = rect.top

            # 鼠标相对base点移到右上角位置
            click_x1 = base1_x + USER_INPUT_OFFSET_X
            click_y1 = base1_y + USER_INPUT_OFFSET_Y
            pyautogui.moveTo(click_x1, click_y1, duration=0.5)
            pyautogui.click(click_x1, click_y1)
            send_keys(username)
            # print(f"已输入用户名，坐标：({click_x1}, {click_y1})")

            click_x2 = base1_x + PWD_INPUT_OFFSET_X
            click_y2 = base1_y + PWD_INPUT_OFFSET_Y
            pyautogui.moveTo(click_x2, click_y2, duration=0.5)
            pyautogui.click(click_x2, click_y2)
            send_keys(password)
            # print(f"已输入密码，坐标：({click_x2}, {click_y2})")

            click_x3 = base1_x + LOGIN_CLICK_OFFSET_X
            click_y3 = base1_y + LOGIN_CLICK_OFFSET_Y
            pyautogui.moveTo(click_x3, click_y3, duration=0.5)
            pyautogui.click(click_x3, click_y3)
            print(f"已完成交易登录")
    except Exception as e:
        print("未找到目标进程或窗口")


    # 等待窗口控件出现
    time.sleep(5)
    # main_win.set_focus()
    des = Desktop(backend="win32")
    # windows = des.windows(class_name="#32770")

    dlg_find = des.window(class_name="#32770", found_index=0)

    dlg_find.set_focus()
    
    pyautogui.press('enter')
    # print("窗口已获得焦点")


if __name__ == "__main__":
    start()