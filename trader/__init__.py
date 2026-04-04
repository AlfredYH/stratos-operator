
import os
import sys

from . import trader
from . import reg

from pathlib import Path
from loguru import logger


# 1. 【核心】动态定位项目根目录
# __file__ 是当前 __init__.py 的路径
# .parent 是 my_package 目录，再一个 .parent 就是 MyProject 根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. 【核心】定义并创建日志文件夹
# 这样无论从哪启动，logger 文件夹永远在根目录下
LOG_DIR = BASE_DIR / "Logger"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 3. 【核心】Loguru 初始化配置
def _init_logging():
    # 移除默认的控制台输出，避免重复
    logger.remove()
    
    # 添加控制台输出 (用于实时查看)
    logger.add(sys.stderr, level="INFO", colorize=True)
    
    # 添加文件输出 (按日期命名，放在根目录的 logger 文件夹)
    log_file_path = LOG_DIR / "{time:YYYYMMDD}.log"
    logger.add(
        log_file_path,
        rotation="00:00",
        retention="60 days",
        encoding="utf-8",
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

# 执行初始化
_init_logging()

__all__ = ["BASE_DIR", "LOG_DIR"]

logger.info(f"项目已初始化。根目录: {BASE_DIR}")


##################################
__version__ = "0.1.0"
__author__ = "Stratos Operator"
##################################


# STRATOS TRADER Logo
# 采用 Slant 风格，拼写：S-T-R-A-T-O-S  T-R-A-D-E-R
logo = r"""
   _____ ________  ___  __________  ____        
  / ___//_  __/ __ \/   |/_  __/ __ \/ ___/        
  \__ \  / / / /_/ / /| |  / / / / / /\__ \         
 ___/ / / / / _, _/ ___ | / / / /_/ /___/ /         
/____/ /_/ /_/ |_/_/  |_|/_/  \____//____/          
                                                    
  __________  ___    ____  __________
 /_  __/ __ \/   |  / __ \/ ____/ __ \
  / / / /_/ / /| | / / / / __/ / /_/ /
 / / / _, _/ ___ |/ /_/ / /___/ _, _/
/_/ /_/ |_/_/  |_/_____/_____/_/ |_/
                                            
    """
# 适配不同系统的清屏
os.system('cls' if os.name == 'nt' else 'clear')

# 打印带颜色的 Logo (终端支持的话会显示青蓝色)
print("\033[96m" + logo + "\033[0m")
print("\033[92m[SYSTEM OK]\033[0m Stratos Trader is now online and synchronized.")