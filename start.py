# -*- coding: utf-8 -*-
"""小t的菜单 - 本地后端启动脚本（避免中文路径编码问题）"""
import subprocess
import sys
import os

PYTHON = r"C:\Users\gyq\.workbuddy\binaries\python\versions\3.13.12\python.exe"
APP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "app.py")

print("=" * 50)
print("  小t的菜单 - 本地服务")
print("=" * 50)
print(f"  Python : {PYTHON}")
print(f"  App    : {APP_FILE}")
print(f"  API    : http://127.0.0.1:8080")
print(f"  访问   : http://localhost:8080")
print("=" * 50)
print()

if not os.path.exists(PYTHON):
    print(f"ERROR: Python 未找到: {PYTHON}")
    input("按 Enter 退出...")
    sys.exit(1)

if not os.path.exists(APP_FILE):
    print(f"ERROR: app.py 未找到: {APP_FILE}")
    input("按 Enter 退出...")
    sys.exit(1)

print("[信息] 正在启动后端服务...")
print("[信息] 启动后请访问：http://localhost:8080")
print("[信息] 关闭此窗口将停止服务")
print("=" * 50)
print()

try:
    subprocess.call([PYTHON, APP_FILE])
except KeyboardInterrupt:
    print("\n[信息] 服务已停止（用户中断）")
except Exception as e:
    print(f"\n[错误] 启动失败: {e}")
    try:
        input("按 Enter 退出...")
    except EOFError:
        pass
    sys.exit(1)
