import sys
import os

# 添加项目路径到 Python 路径
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from run import app as application  # 导入 Flask 应用实例