

from . import trader
from . import reg

import os


# 修正后的 STRATOS TRADER 极客 Logo
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