# 小t的菜单 - PythonAnywhere + TiDB Cloud 完整部署指南

> **目标**：把你的点菜 App 部署到云端，让不同手机都能访问，数据不丢失
> 
> **预计时间**：40-60 分钟（第一次部署可能慢一点，熟悉后 15 分钟搞定）
> 
> **费用**：**完全免费**，不需要信用卡

---

## 📋 部署架构图

```
用户手机/电脑
    ↓ 访问前端（GitHub Pages，免费）
    ↓ 
前端页面（静态HTML/CSS/JS）
    ↓ 调用 API（相对路径 /api/...）
    ↓
PythonAnywhere（免费 Flask 后端）
    ↓ 连接数据库
    ↓
TiDB Cloud Serverless（免费 MySQL 协议数据库）
```

**数据流向**：
1. 用户打开前端页面（GitHub Pages）
2. 前端调用 `/api/chefs` 等接口
3. 请求发送到 PythonAnywhere 的后端
4. 后端从 TiDB Cloud 读取数据
5. 数据返回前端，展示给用户

---

## 🚀 第一步：注册 TiDB Cloud（5-10 分钟）

TiDB Cloud 是我们的云端数据库，用来存储菜品、大厨、订单等数据。

### 1.1 注册账号

1. 打开浏览器，访问：**https://tidbcloud.com/**
2. 点击右上角 **"Sign Up"** 按钮
3. 选择注册方式（推荐用 GitHub 或 Google 账号注册，更快）：
   - 如果选 **"Continue with GitHub"**：会跳转到 GitHub 授权页面，点 "Authorize" 即可
   - 如果选 **"Continue with Google"**：选你的 Google 账号即可
   - 如果选 **"Email"**：输入邮箱，设置密码，然后去邮箱验证

4. 注册完成后，会自动进入 TiDB Cloud 控制台

### 1.2 创建 Serverless 集群（免费）

1. 在控制台首页，点击 **"Create Cluster"**（创建集群）
2. 选择 **"Serverless"**（免费版）：
   - 看到 **"Free"** 标签的就是免费版
   - 点击 **"Select"** 按钮
3. 配置集群：
   - **Cluster Name**（集群名称）：输入 `xiaot-menu-db`（可以随便取）
   - **Cloud Provider**（云服务商）：选 **"AWS"**（亚马逊云，稳定）
   - **Region**（地区）：选 **"ap-southeast-1 (Singapore)"**（新加坡，国内访问快）
   - 点击 **"Next"**
4. 设置访问权限（重要！）：
   - 看到 **"Allowed IP Addresses"**（允许的 IP 地址）
   - 先不急着填，我们后面再来配置（也可以现在就选 "Allow Access from Anywhere"，但不安全）
   - 点击 **"Create"**
5. 等待集群创建（约 1-3 分钟）：
   - 看到 **"Cluster Status: Available"** 就表示创建成功了

### 1.3 获取数据库连接信息

1. 在集群详情页，点击 **"Connect"** 按钮
2. 选择 **"Connect with MySQL CLI"**（用 MySQL 命令行连接）
3. 看到连接信息：
   ```
   mysql -h xxx.tidbcloud.com -P 4000 -u root -p
   ```
   - 记下 **Host**（主机地址，类似 `xxx.tidbcloud.com`）
   - 记下 **Port**（端口，一般是 `4000`）
   - 记下 **User**（用户名，一般是 `root`）
4. 设置密码：
   - 点击 **"Generate Password"**（生成密码）或 **"Set Password"**（设置密码）
   - **重要**：把密码记下来！后面要用到
   - 密码要包含大小写字母、数字、特殊字符

### 1.4 创建数据库和表

1. 在集群详情页，点击 **"Open in Web SQL Shell"**（在网页 SQL 编辑器中打开）
2. 等待编辑器加载（约 10 秒）
3. 在 SQL 编辑器中输入以下命令（一行一行执行）：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS xiaot_menu;

-- 使用数据库
USE xiaot_menu;

-- 创建大厨表
CREATE TABLE IF NOT EXISTS chefs (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    img VARCHAR(255),
    emoji VARCHAR(10),
    role VARCHAR(100),
    tag VARCHAR(100)
);

-- 创建分类表
CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(50) PRIMARY KEY,
    label VARCHAR(100) NOT NULL
);

-- 创建菜品表
CREATE TABLE IF NOT EXISTS dishes (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cat VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    desc TEXT,
    gradient VARCHAR(100),
    chef_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    chef_id VARCHAR(50),
    items JSON,
    total_price DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入初始数据（大厨）
INSERT INTO chefs (id, name, img, emoji, role, tag) VALUES
('lulu', '水豚噜噜', 'assets/images/2_68.png', '🐹', '汤品专家 🥣', '汤品超好喝~'),
('nailong', '奶龙', 'assets/images/2_70.png', '🐲', '荤菜大师 🍖', '荤菜一绝！'),
('beini', '小恐龙贝尼', 'assets/images/2_72.png', '🦕', '素菜达人 🥬', '素菜也好吃！');

-- 插入初始数据（分类）
INSERT INTO categories (id, label) VALUES
('all', '所有菜品'),
('soup', '汤品🥣'),
('meat', '荤菜🍖'),
('veg', '素菜🥬');

-- 插入初始数据（菜品）
INSERT INTO dishes (id, name, cat, price, desc, gradient, chef_id) VALUES
('luandantang', '蛋花汤', 'soup', 12.00, '清淡鲜美，营养丰富~', 'var(--gradient-orange)', 'lulu'),
('fqdt', '番茄蛋汤', 'soup', 15.00, '酸甜可口，暖心暖胃~', 'var(--gradient-orange)', 'lulu'),
('cnl', '炒奶龙', 'meat', 28.00, '鲜嫩多汁，肉香四溢~', 'var(--gradient-orange)', 'nailong'),
('kxdg', '咖喱土豆鸡', 'meat', 32.00, '浓郁咖喱，鸡肉嫩滑~', 'var(--gradient-green)', 'nailong'),
('cc', '炒青菜', 'veg', 10.00, '清爽解腻，健康美味~', 'var(--gradient-green)', 'beini');

-- 查看数据是否插入成功
SELECT * FROM chefs;
SELECT * FROM dishes;
```

4. 点击 **"Run"** 按钮执行 SQL
5. 如果看到数据，说明数据库配置成功！

### 1.5 获取完整的数据库连接字符串

把以下信息记下来（后面要用到）：

```
Host:      xxx.tidbcloud.com  （你的集群地址）
Port:      4000
User:      root
Password:  xxxxxxxx           （你设置的密码）
Database:  xiaot_menu
```

连接字符串格式（MySQL 协议）：
```
mysql+pymysql://root:密码@ Host:4000/xiaot_menu?charset=utf8mb4
```

**例如**：
```
mysql+pymysql://root:Abc12345@xyz.tidbcloud.com:4000/xiaot_menu?charset=utf8mb4
```

---

## 🚀 第二步：准备 GitHub 仓库（10-15 分钟）

PythonAnywhere 需要从 GitHub 拉取代码，所以我们需要先把代码推送到 GitHub。

### 2.1 注册 GitHub 账号（如果还没有）

1. 访问：**https://github.com/**
2. 点击 **"Sign up"**
3. 输入用户名、邮箱、密码
4. 验证邮箱

### 2.2 创建新仓库

1. 登录 GitHub，点击右上角 **"+"** → **"New repository"**
2. 填写仓库信息：
   - **Repository name**（仓库名）：输入 `xiaot-menu`（可以随便取）
   - **Description**（描述）：输入 `小t的菜单 - 虚拟大厨点菜App`
   - 选择 **"Public"**（公开，免费用户只能创建公开仓库）
   - ✅ 勾选 **"Add a README file"**
   - 点击 **"Create repository"**

### 2.3 把代码推送到 GitHub

**方法一：用 GitHub Desktop（推荐，最简单）**

1. 下载安装 **GitHub Desktop**：https://desktop.github.com/
2. 登录你的 GitHub 账号
3. 点击 **"File"** → **"Clone repository"**
4. 选择你刚创建的仓库 `xiaot-menu`，选择本地路径（比如 `D:\codebuddy\小t的菜单app`）
5. 把你的项目文件复制到这个文件夹里
6. 在 GitHub Desktop 里，看到文件变化，填写提交信息：
   - **Summary**（摘要）：输入 `初始提交：小t的菜单后端和前端`
   - 点击 **"Commit to main"**
7. 点击 **"Push origin"**（推送到远程）

**方法二：用命令行（如果你会用 Git）**

```bash
# 进入项目目录
cd "D:\codebuddy\小t的菜单app"

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "初始提交：小t的菜单后端和前端"

# 关联远程仓库（把下面的 XXX 换成你的 GitHub 用户名）
git remote add origin https://github.com/XXX/xiaot-menu.git

# 推送
git push -u origin main
```

### 2.4 确认代码已推送

1. 打开你的 GitHub 仓库页面
2. 应该能看到所有文件：
   - `server/` 文件夹（后端代码）
   - `dist/` 文件夹（前端代码）
   - `server/requirements.txt`（依赖清单）
   - 其他文件...

---

## 🚀 第三步：部署后端到 PythonAnywhere（15-20 分钟）

PythonAnywhere 是一个免费的 Python 托管平台，可以运行 Flask、Django 等应用。

### 3.1 注册 PythonAnywhere 账号

1. 访问：**https://www.pythonanywhere.com/**
2. 点击 **"Create a Beginner account"**（创建免费账号）
3. 填写用户名、邮箱、密码
4. 验证邮箱
5. 登录后，进入 **"Dashboard"**（控制台）

### 3.2 配置 Python 版本和虚拟环境

1. 在 Dashboard，点击 **"Consoles"** → **"Bash"**（打开命令行）
2. 在命令行中输入以下命令（一行一行执行）：

```bash
# 创建虚拟环境（推荐使用 Python 3.10）
mkvirtualenv --python=/usr/bin/python3.10 xiaot-menu-env

# 看到 (xiaot-menu-env) 就表示虚拟环境创建成功
```

### 3.3 从 GitHub 拉取代码

1. 在 Bash 命令行中继续输入：

```bash
# 进入虚拟环境目录
cd ~

# 克隆你的 GitHub 仓库（把 XXX 换成你的 GitHub 用户名）
git clone https://github.com/XXX/xiaot-menu.git

# 看到 "xiaot-menu" 文件夹就表示克隆成功
```

### 3.4 安装依赖包

1. 进入项目目录，安装依赖：

```bash
# 进入项目目录
cd xiaot-menu/server

# 激活虚拟环境
workon xiaot-menu-env

# 安装依赖包
pip install -r requirements.txt

# 看到 "Successfully installed..." 就表示安装成功
```

**重要**：确保 `requirements.txt` 包含以下内容：
```
flask
flask-cors
pymysql
gunicorn
```

如果没有，手动安装：
```bash
pip install flask flask-cors pymysql gunicorn
```

### 3.5 配置环境变量（连接 TiDB Cloud）

1. 在 Bash 命令行中，创建环境变量配置文件：

```bash
# 回到项目根目录
cd ~/xiaot-menu

# 创建 .env 文件（用来存储敏感信息）
nano .env
```

2. 在 nano 编辑器中输入以下内容（把数据库连接信息换成你自己的）：

```
DATABASE_URL=mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4
```

3. 按 `Ctrl + O` 保存，按 `Enter` 确认，按 `Ctrl + X` 退出

### 3.6 修改 app.py 支持读取环境变量

确保你的 `server/app.py` 开头有以下代码（用来读取环境变量）：

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接字符串
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data.db')
```

如果你没有 `python-dotenv` 包，安装一下：
```bash
pip install python-dotenv
```

然后在 `server/` 目录下创建 `.env` 文件（同 3.5 步骤）。

### 3.7 创建 PythonAnywhere Web 应用

1. 回到 PythonAnywhere Dashboard
2. 点击 **"Web"** → **"Add a new web app"**
3. 选择 **"Manual configuration"**（手动配置）
4. 选择 **"Python 3.10"**
5. 点击 **"Next"** 完成创建

### 3.8 配置 Web 应用

1. 在 Web 应用配置页面，找到以下设置并修改：

**① Source code**（源代码路径）：
   - 输入：`/home/你的用户名/xiaot-menu/server`

**② Working directory**（工作目录）：
   - 输入：`/home/你的用户名/xiaot-menu/server`

**③ Virtual environment**（虚拟环境路径）：
   - 输入：`/home/你的用户名/.virtualenvs/xiaot-menu-env`

**④ WSGI configuration file**（WSGI 配置文件）：
   - 点击路径链接，编辑文件
   - 把内容改成以下代码：

```python
import sys
import os

# 把项目目录加入到 Python 路径
path = '/home/你的用户名/xiaot-menu/server'
if path not in sys.path:
    sys.path.append(path)

# 设置环境变量
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4'

# 导入 Flask 应用
from app import app as application
```

   - 点击 **"Save"** 保存

2. 在 Web 应用配置页面，找到 **"Environment variables"**（环境变量）：
   - 点击 **"Environment variables"** 标签
   - 添加环境变量：
     - **Name**: `DATABASE_URL`
     - **Value**: `mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4`
   - 点击 **"Save"**

### 3.9 启动 Web 应用

1. 在 Web 应用配置页面，点击 **"Reload"** 按钮
2. 等待约 10 秒
3. 看到 **"Your app is running at: https://你的用户名.pythonanywhere.com"** 就表示成功！

### 3.10 测试后端 API

1. 打开浏览器，访问：`https://你的用户名.pythonanywhere.com/api/chefs`
2. 如果看到 JSON 数据（大厨列表），说明后端部署成功！
3. 如果看到错误，点击 **"Web"** → **"Log files"** 查看错误日志

---

## 🚀 第四步：部署前端到 GitHub Pages（5-10 分钟）

前端是静态文件（HTML/CSS/JS），可以免费托管在 GitHub Pages。

### 4.1 修改前端 API 地址

因为前端需要调用后端 API，我们需要修改 `dist/data.js`，让它指向 PythonAnywhere 的地址。

1. 打开 `dist/data.js`
2. 找到 API 调用部分，把地址改成：

```javascript
// 原来的（本地开发用）
const API_BASE = '/api';

// 改成（生产环境用）
const API_BASE = 'https://你的用户名.pythonanywhere.com/api';
```

3. 保存文件，推送到 GitHub

### 4.2 启用 GitHub Pages

1. 打开你的 GitHub 仓库页面
2. 点击 **"Settings"**（设置）
3. 在左侧菜单找到 **"Pages"**
4. 在 **"Source"** 部分：
   - 选择 **"Deploy from a branch"**
   - **Branch**（分支）：选择 `main`，文件夹选择 `/dist`
   - 点击 **"Save"**
5. 等待约 1-3 分钟
6. 看到 **"Your site is published at https://你的用户名.github.io/xiaot-menu/"** 就表示成功！

### 4.3 测试前端

1. 打开浏览器，访问：`https://你的用户名.github.io/xiaot-menu/`
2. 应该能看到点菜 App 的界面
3. 打开浏览器开发者工具（F12），查看 **"Network"** 标签
4. 刷新页面，应该能看到 API 请求发送到 PythonAnywhere
5. 如果数据能正常加载，说明前后端都部署成功了！

---

## 🚀 第五步：配置 TiDB Cloud 访问权限（重要！）

PythonAnywhere 的服务器 IP 地址是固定的，我们需要在 TiDB Cloud 中允许这个 IP 访问数据库。

### 5.1 获取 PythonAnywhere 的 IP 地址

1. 在 PythonAnywhere 的 Bash 命令行中输入：
```bash
curl ifconfig.me
```
2. 会返回一个 IP 地址（记下来）

### 5.2 在 TiDB Cloud 中添加 IP 白名单

1. 打开 TiDB Cloud 控制台
2. 进入你的集群详情页
3. 点击 **"Settings"** → **"Network Access"**
4. 点击 **"Add Access Control"**
5. 输入 PythonAnywhere 的 IP 地址（或者选 "Allow Access from Anywhere"，但不安全）
6. 点击 **"Confirm"**

---

## 🎯 第六步：测试和验证

### 6.1 功能测试清单

- [ ] 打开前端页面，能看到大厨列表
- [ ] 点击大厨，能看到菜品列表
- [ ] 添加菜品到购物车，能正常显示
- [ ] 提交订单，能在后端数据库中看到订单记录
- [ ] 用不同手机/电脑访问，数据能同步

### 6.2 用手机测试

1. 在手机浏览器中访问：`https://你的用户名.github.io/xiaot-menu/`
2. 测试所有功能
3. 如果朋友也想测试，把链接发给他们

---

## 🛠️ 常见问题 and 解决方案

### 问题 1：后端部署后访问显示 "Internal Server Error"

**原因**：代码有错误，或者环境变量没配置对

**解决**：
1. 在 PythonAnywhere Dashboard，点击 **"Web"** → **"Log files"** → **"Error log"**
2. 查看具体错误信息
3. 常见问题：
   - `DATABASE_URL` 环境变量没配置或配置错误
   - `pymysql` 没安装
   - `app.py` 中有语法错误

### 问题 2：前端访问后端 API 时报 CORS 错误

**原因**：后端没有配置 CORS（跨域资源共享）

**解决**：
1. 确保 `server/app.py` 中有以下代码：
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # 允许所有域名访问
```

2. 如果只想允许特定域名访问：
```python
CORS(app, resources={r"/api/*": {"origins": "https://你的用户名.github.io"}})
```

### 问题 3：TiDB Cloud 连接失败

**原因**：IP 白名单没配置，或者连接字符串错误

**解决**：
1. 检查 TiDB Cloud 的 IP 白名单是否包含 PythonAnywhere 的 IP
2. 检查连接字符串格式是否正确
3. 在 PythonAnywhere Bash 中测试连接：
```bash
mysql -h 你的Host -P 4000 -u root -p
```
输入密码，如果能连上说明网络没问题

### 问题 4：修改代码后，PythonAnywhere 没有更新

**原因**：没有重新拉取 GitHub 代码，或者没有重启 Web 应用

**解决**：
1. 在 PythonAnywhere Bash 中：
```bash
cd ~/xiaot-menu
git pull origin main
```
2. 在 PythonAnywhere Dashboard，**"Web"** → 点击 **"Reload"**

---

## 📝 部署检查清单

- [ ] TiDB Cloud 集群已创建
- [ ] 数据库和表已创建
- [ ] 初始数据已插入
- [ ] 代码已推送到 GitHub
- [ ] PythonAnywhere 账号已注册
- [ ] 后端已部署到 PythonAnywhere
- [ ] 环境变量已配置
- [ ] 前端已部署到 GitHub Pages
- [ ] TiDB Cloud IP 白名单已配置
- [ ] 前后端能正常通信
- [ ] 用手机测试成功

---

## 🎉 部署完成！

恭喜你！现在你的点菜 App 已经部署到云端了：

- **前端地址**：`https://你的用户名.github.io/xiaot-menu/`
- **后端地址**：`https://你的用户名.pythonanywhere.com/`

**下一步可以做什么**：
1. 分享链接给朋友，让他们也能点菜
2. 继续开发新功能（比如用户登录、支付集成等）
3. 学习更多后端知识，优化性能和安全性

---

## 📚 附录：常用命令

### PythonAnywhere Bash 常用命令

```bash
# 进入项目目录
cd ~/xiaot-menu

# 拉取最新代码
git pull origin main

# 查看日志
tail -f /var/log/你的用户名.pythonanywhere.com.error.log

# 重启 Web 应用（也可以在 Dashboard 点击 Reload）
touch /var/www/你的用户名_pythonanywhere_com_wsgi.py
```

### TiDB Cloud SQL 常用命令

```sql
-- 查看所有数据库
SHOW DATABASES;

-- 使用数据库
USE xiaot_menu;

-- 查看所有表
SHOW TABLES;

-- 查看菜品
SELECT * FROM dishes;

-- 添加新菜品
INSERT INTO dishes (id, name, cat, price, desc, gradient, chef_id) 
VALUES ('new_dish', '新菜品', 'soup', 18.00, '好吃的~', 'var(--gradient-orange)', 'lulu');

-- 删除菜品
DELETE FROM dishes WHERE id = 'new_dish';
```

---

**文档版本**：v1.0  
**最后更新**：2026-06-27  
**作者**：小t的菜单开发团队
