# ═══════════════════════════════════════════════════════
#  小t的菜单 — PythonAnywhere WSGI 入口文件
#
#  PythonAnywhere 会自动加载此文件，导出 `application` 变量。
#  部署时将此文件内容复制到 PythonAnywhere 的 WSGI 配置文件中，
#  或直接在 WSGI 配置文件中 import 此模块。
#
#  使用方式（在 PythonAnywhere Web 配置页面的 WSGI 文件中）：
#    import sys, os
#    sys.path.insert(0, '/home/你的用户名/xiaot-menu/server')
#    from wsgi import application
# ═══════════════════════════════════════════════════════

import os
import sys

# 确保项目目录在 Python 路径中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── 设置环境变量（连接 TiDB Cloud）──
# 方式一：在此处直接设置（不推荐，密码会暴露在代码中）
# os.environ['DATABASE_URL'] = 'mysql://user:pass@host:4000/db'

# 方式二（推荐）：在 PythonAnywhere Web 配置页面的
#   "Environment variables" 中设置 DATABASE_URL

# 导入 Flask 应用
from app import app as application

# PythonAnywhere 导入模块时会触发 db.py 的 init_db() 和 seed_from_test_data()
# 无需额外调用
