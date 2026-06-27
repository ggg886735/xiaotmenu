# 小t的菜单 — Gitee Pages + PythonAnywhere 完整部署指南

> **目标**：把点菜 App 部署到云端，国内访问快，数据不丢失
> 
> **预计时间**：50-70 分钟（第一次部署，熟悉后 20 分钟搞定）
> 
> **费用**：**完全免费**，不需要信用卡，但需要 Gitee 实名认证

---

## 📋 部署架构图

```
国内用户（手机/电脑）
    ↓ 访问前端（Gitee Pages，国内服务器，速度快）
    ↓ 
前端页面（静态 HTML/CSS/JS）
    ↓ 调用 API（指向 PythonAnywhere 后端地址）
    ↓
PythonAnywhere（免费 Flask 后端，国外服务器）
    ↓ 连接数据库
    ↓
TiDB Cloud Serverless（免费 MySQL 协议数据库，新加坡节点）
```

**数据流向**：
1. 用户打开 Gitee Pages 前端页面
2. 前端 JS 调用 `https://你的用户名.pythonanywhere.com/api/...`
3. PythonAnywhere 后端接收请求，查询 TiDB Cloud 数据库
4. 数据返回前端，展示给用户
5. 不同手机/电脑访问同一个链接，数据完全同步

---

## 🚀 第一步：注册 TiDB Cloud 并建库（10-15 分钟）

TiDB Cloud 是免费的 MySQL 协议兼容数据库，用来存储菜品、大厨等数据。

### 1.1 注册 TiDB Cloud 账号

1. 打开浏览器，访问：**https://tidbcloud.com/**
2. 点击右上角 **"Sign Up"** 按钮
3. 推荐用 GitHub 或 Google 账号注册（更快）：
   - 选 **"Continue with GitHub"** → 跳转到 GitHub 授权 → 点 "Authorize"
   - 选 **"Continue with Google"** → 选择你的 Google 账号
4. 注册完成后，自动进入 TiDB Cloud 控制台

### 1.2 创建 Serverless 集群（免费）

1. 控制台首页，点击 **"Create Cluster"**
2. 选择 **"Serverless"**（免费版，有 **"Free"** 标签）
3. 配置集群：
   - **Cluster Name**：输入 `xiaot-menu-db`（可随便取）
   - **Cloud Provider**：选 **"AWS"**
   - **Region**：选 **"ap-southeast-1 (Singapore)"**（新加坡，国内访问相对快）
   - 点击 **"Next"**
4. 设置访问权限：
   - 暂时先不选 "Allow Access from Anywhere"（不安全）
   - 后面部署到 PythonAnywhere 后，再把 PythonAnywhere 的 IP 加进去
   - 点击 **"Create"**
5. 等待集群创建（约 1-3 分钟），看到 **"Cluster Status: Available"** 就成功了

### 1.3 获取数据库连接信息

1. 在集群详情页，点击 **"Connect"** 按钮
2. 选择 **"Connect with MySQL CLI"**
3. 记录连接信息（后面要用到）：
   ```
   Host:      xxx.tidbcloud.com  （你的集群地址）
   Port:      4000
   User:      root
   Password:   （点击 "Generate Password" 设置一个，记下来！）
   ```
4. **重要**：密码要包含大小写字母、数字、特殊字符，并妥善保存！

### 1.4 在网页 SQL 编辑器中建表和插入初始数据

1. 在集群详情页，点击 **"Open in Web SQL Shell"**
2. 等待 SQL 编辑器加载（约 10 秒）
3. 输入以下 SQL 命令（一行一行执行，点击 "Run" 按钮）：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS xiaot_menu;

-- 使用数据库
USE xiaot_menu;

-- 创建大厨表
CREATE TABLE IF NOT EXISTS chefs (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    img TEXT NOT NULL DEFAULT '',
    emoji VARCHAR(16) NOT NULL DEFAULT '',
    role VARCHAR(64) NOT NULL DEFAULT '',
    tag VARCHAR(128) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建分类表
CREATE TABLE IF NOT EXISTS categories (
    `key` VARCHAR(32) PRIMARY KEY,
    label VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建菜品表
CREATE TABLE IF NOT EXISTS dishes (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    cat VARCHAR(16) NOT NULL DEFAULT 'veg',
    price INTEGER NOT NULL DEFAULT 0,
    `desc` TEXT NOT NULL DEFAULT '',
    gradient VARCHAR(64) NOT NULL DEFAULT 'var(--gradient-orange)',
    image TEXT,
    created_at DATETIME NOT NULL DEFAULT NOW(),
    updated_at DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建用户状态表（记录选中的大厨和购物车）
CREATE TABLE IF NOT EXISTS user_state (
    id INT PRIMARY KEY DEFAULT 1,
    selected_chef VARCHAR(64) NOT NULL DEFAULT 'lulu',
    cart_json TEXT NOT NULL DEFAULT '[]'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入初始数据：大厨
INSERT IGNORE INTO chefs (id, name, img, emoji, role, tag) VALUES
('lulu', '水豚噜噜', 'assets/images/2_68.png', '🐹', '汤品专家 🥣', '汤品超好喝~'),
('nailong', '奶龙', 'assets/images/2_70.png', '🐲', '荤菜大师 🍖', '荤菜一绝！'),
('beini', '小恐龙贝尼', 'assets/images/2_72.png', '🦕', '素菜达人 🥬', '素菜也好吃！');

-- 插入初始数据：分类
INSERT IGNORE INTO categories (`key`, label) VALUES
('all', '所有菜品'),
('soup', '汤品🥣'),
('meat', '荤菜🍖'),
('veg', '素菜🥬');

-- 插入初始数据：菜品
INSERT IGNORE INTO dishes (id, name, cat, price, `desc`, gradient, image) VALUES
('luandantang', '蛋花汤', 'soup', 12.00, '清淡鲜美，营养丰富~', 'var(--gradient-orange)', NULL),
('fqdt', '番茄蛋汤', 'soup', 15.00, '酸甜可口，暖心暖胃~', 'var(--gradient-orange)', NULL),
('cnl', '炒奶龙', 'meat', 28.00, '鲜嫩多汁，肉香四溢~', 'var(--gradient-orange)', NULL),
('kxdg', '咖喱土豆鸡', 'meat', 32.00, '浓郁咖喱，鸡肉嫩滑~', 'var(--gradient-green)', NULL),
('cc', '炒青菜', 'veg', 10.00, '清爽解腻，健康美味~', 'var(--gradient-green)', NULL);

-- 初始化用户状态表
INSERT IGNORE INTO user_state (id, selected_chef, cart_json) VALUES (1, 'lulu', '[]');

-- 验证数据是否插入成功
SELECT * FROM chefs;
SELECT * FROM dishes;
```

4. 如果看到数据，说明数据库配置成功！

### 1.5 记录数据库连接字符串

把以下信息整理好（后面配置 PythonAnywhere 时要用到）：

```
Host:       xxx.tidbcloud.com  （你的集群地址）
Port:       4000
User:       root
Password:   xxxxxxxx          （你设置的密码）
Database:   xiaot_menu
```

**连接字符串格式**（后面配置时要用的）：
```
mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4
```

**例如**：
```
mysql+pymysql://root:Abc12345@xyz.tidbcloud.com:4000/xiaot_menu?charset=utf8mb4
```

---

## 🚀 第二步：注册 Gitee 并实名认证（1-2 天）

Gitee 是中国版的 GitHub，服务器在国内，访问速度快。

### 2.1 注册 Gitee 账号

1. 访问：**https://gitee.com/**
2. 点击右上角 **"注册"**
3. 填写用户名、邮箱、密码
4. 验证邮箱

### 2.2 实名认证（必须，否则不能创建私有仓库和使用 Gitee Pages）

1. 登录 Gitee，点击右上角头像 → **"设置"**
2. 在左侧菜单找到 **"实名认证"**
3. 填写真实姓名、身份证号
4. 上传身份证正面照片（清晰、完整）
5. 提交审核（约 1-2 个工作日）

**注意**：实名认证是必须的，因为 Gitee Pages 功能只对实名认证用户开放。

---

## 🚀 第三步：准备代码并推送到 Gitee（10-15 分钟）

### 3.1 修改前端 API 地址（重要！）

部署到生产环境前，需要把 `dist/data.js` 中的 `API_BASE` 改成你的 PythonAnywhere 地址。

**但现在先不改**，因为 PythonAnywhere 地址还没创建。我们先推本地开发版本的代码到 Gitee，等 PythonAnywhere 部署完成后，再修改 `API_BASE` 并重新推送。

**当前 `dist/data.js` 第 17 行**：
```javascript
const API_BASE = '/api';  // ← 本地开发用，生产环境要改
```

### 3.2 创建 Gitee 仓库

1. 登录 Gitee，点击右上角 **"+"** → **"新建仓库"**
2. 填写仓库信息：
   - **仓库名称**：输入 `xiaot-menu`
   - **仓库介绍**：输入 `小t的菜单 - 虚拟大厨点菜App`
   - **是否开源**：选 **"私有"**（免费用户只能创建私有仓库）
   - ✅ 勾选 **"使用 README 文件初始化仓库"**
   - 点击 **"创建"**

### 3.3 把代码推送到 Gitee

**方法一：用命令行（推荐）**

1. 打开 Bash 命令行（Git Bash 或 WSL）
2. 进入项目目录：
```bash
cd "D:\codebuddy\小t的菜单app"
```

3. 初始化 Git 仓库（如果还没初始化的话）：
```bash
git init
```

4. 添加文件到 Git：
```bash
git add .
```

5. 提交：
```bash
git commit -m "初始提交：小t的菜单后端和前端"
```

6. 关联 Gitee 远程仓库（把 `你的用户名` 换成你的 Gitee 用户名）：
```bash
git remote add origin https://gitee.com/你的用户名/xiaot-menu.git
```

7. 推送代码：
```bash
git push -u origin master
```

**如果遇到推送失败**：
- 确保 Gitee 用户名和密码正确
- 如果是第一次推送，可能需要输入 Gitee 账号密码

**方法二：用 Gitee 桌面客户端**

1. 下载安装 **Gitee Desktop**（https://gitee.com/help/articles/4262）
2. 登录 Gitee 账号
3. 克隆你的仓库到本地
4. 把项目文件复制到克隆的文件夹
5. 提交并推送

---

## 🚀 第四步：部署后端到 PythonAnywhere（15-20 分钟）

### 4.1 注册 PythonAnywhere 账号

1. 访问：**https://www.pythonanywhere.com/**
2. 点击 **"Create a Beginner account"**（创建免费账号）
3. 填写用户名、邮箱、密码
4. 验证邮箱
5. 登录后，进入 **"Dashboard"**（控制台）

### 4.2 配置 Python 虚拟环境

1. 在 Dashboard，点击 **"Consoles"** → **"Bash"**（打开命令行）
2. 输入以下命令：

```bash
# 创建虚拟环境（Python 3.10）
mkvirtualenv --python=/usr/bin/python3.10 xiaot-menu-env

# 看到 (xiaot-menu-env) 就表示成功
```

### 4.3 从 Gitee 拉取代码

1. 在 Bash 中继续输入：

```bash
# 进入主目录
cd ~

# 克隆 Gitee 仓库（把 你的用户名 换成你的 Gitee 用户名）
git clone https://gitee.com/你的用户名/xiaot-menu.git

# 看到 xiaot-menu 文件夹就表示成功
```

**如果克隆失败**（Gitee 私有仓库需要密码）：
- 输入 Gitee 用户名和密码
- 或者配置 SSH 密钥（推荐，更安全）

### 4.4 安装依赖包

```bash
# 进入项目目录
cd xiaot-menu/server

# 激活虚拟环境
workon xiaot-menu-env

# 安装依赖
pip install -r requirements.txt

# 如果 requirements.txt 有问题，手动安装：
pip install flask flask-cors pymysql gunicorn
```

### 4.5 配置环境变量（连接 TiDB Cloud）

1. 在 Bash 中，创建配置文件：

```bash
# 回到项目根目录
cd ~/xiaot-menu

# 创建 .env 文件
nano .env
```

2. 在 nano 编辑器中输入以下内容（把数据库连接信息换成你自己的）：

```
DATABASE_URL=mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4
```

3. 按 `Ctrl + O` 保存，按 `Enter` 确认，按 `Ctrl + X` 退出

### 4.6 修改 app.py 支持读取环境变量

确保 `server/app.py` 开头有以下代码（用来读取环境变量）：

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接字符串
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data.db')
```

如果缺少 `python-dotenv` 包，安装一下：
```bash
pip install python-dotenv
```

然后在 `server/` 目录下创建 `.env` 文件（同 4.5 步骤）。

### 4.7 创建 PythonAnywhere Web 应用

1. 回到 PythonAnywhere Dashboard
2. 点击 **"Web"** → **"Add a new web app"**
3. 点击 **"Next"**（跳过 "Manual configuration" 选择）
4. 选择 **"Python 3.10"**
5. 点击 **"Next"** 完成创建

### 4.8 配置 Web 应用

1. 在 Web 应用配置页面，找到以下设置并修改：

**① Source code**（源代码路径）：
   - 输入：`/home/你的用户名/xiaot-menu/server`

**② Working directory**（工作目录）：
   - 输入：`/home/你的用户名/xiaot-menu/server`

**③ Virtual environment**（虚拟环境路径）：
   - 输入：`/home/你的用户名/.virtualenvs/xiaot-menu-env`

**④ WSGI configuration file**（WSGI 配置文件）：
   - 点击路径链接，编辑文件
   - 把内容改成以下代码（把 `你的用户名` 换成你的 PythonAnywhere 用户名，把数据库连接信息换成你自己的）：

```python
import sys
import os

# 把项目目录加入到 Python 路径
path = '/home/你的用户名/xiaot-menu/server'
if path not in sys.path:
    sys.path.append(path)

# 设置环境变量（数据库连接）
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4'

# 导入 Flask 应用
from app import app as application
```

   - 点击 **"Save"**

2. 在 Web 应用配置页面，找到 **"Environment variables"**：
   - 点击 **"Environment variables"** 标签
   - 添加环境变量：
     - **Name**: `DATABASE_URL`
     - **Value**: `mysql+pymysql://root:你的密码@你的Host:4000/xiaot_menu?charset=utf8mb4`
   - 点击 **"Save"**

### 4.9 启动 Web 应用

1. 在 Web 应用配置页面，点击 **"Reload"** 按钮
2. 等待约 10 秒
3. 看到 **"Your app is running at: https://你的用户名.pythonanywhere.com"** 就表示成功！

### 4.10 测试后端 API

1. 打开浏览器，访问：`https://你的用户名.pythonanywhere.com/api/chefs`
2. 如果看到 JSON 数据（大厨列表），说明后端部署成功！
3. 如果看到错误，点击 **"Web"** → **"Log files"** 查看错误日志

---

## 🚀 第五步：修改前端 API 地址并重新推送（5 分钟）

现在后端地址已经创建，需要把前端代码中的 `API_BASE` 改成生产环境地址。

### 5.1 修改 dist/data.js

1. 打开 `dist/data.js`
2. 找到第 17 行：
```javascript
const API_BASE = '/api';  // ← 本地开发用，生产环境要改
```
3. 改成：
```javascript
const API_BASE = 'https://你的用户名.pythonanywhere.com/api';  // ← 改成你的 PythonAnywhere 地址
```
4. 保存文件

### 5.2 重新推送代码到 Gitee

```bash
cd "D:\codebuddy\小t的菜单app"
git add dist/data.js
git commit -m "修改 API_BASE 为生产环境地址"
git push origin master
```

---

## 🚀 第六步：部署前端到 Gitee Pages（5-10 分钟）

### 6.1 启用 Gitee Pages

1. 打开你的 Gitee 仓库页面
2. 点击 **"服务"** → **"Pages"**
3. 填写配置：
   - **部署分支**：选择 `master`
   - **部署目录**：输入 `dist`
   - **自定义域名**（可选）：如果你有自己的域名，可以填写
4. 点击 **"启动"**
5. 等待约 1-3 分钟
6. 看到 **"您的 Pages 已经部署成功"** 就表示成功！

### 6.2 访问前端

- 访问地址：`https://你的用户名.gitee.io/xiaot-menu/`
- 应该能看到点菜 App 的界面

---

## 🚀 第七步：配置 TiDB Cloud 访问权限（重要！）

PythonAnywhere 的服务器 IP 地址是固定的，需要在 TiDB Cloud 中允许这个 IP 访问数据库。

### 7.1 获取 PythonAnywhere 的 IP 地址

1. 在 PythonAnywhere 的 Bash 命令行中输入：
```bash
curl ifconfig.me
```
2. 会返回一个 IP 地址（记下来）

### 7.2 在 TiDB Cloud 中添加 IP 白名单

1. 打开 TiDB Cloud 控制台
2. 进入你的集群详情页
3. 点击 **"Overview"** → **"Network Access"**
4. 点击 **"Add IP to Allowlist"**
5. 输入 PythonAnywhere 的 IP 地址
6. 点击 **"Confirm"**

---

## 🎯 第八步：测试和验证

### 8.1 功能测试清单

- [ ] 打开前端页面，能看到大厨列表
- [ ] 点击大厨，能看到菜品列表
- [ ] 添加菜品到购物车，能正常显示
- [ ] 提交订单，能在后端数据库中看到订单记录
- [ ] 用不同手机/电脑访问，数据能同步

### 8.2 用手机测试

1. 在手机浏览器中访问：`https://你的用户名.gitee.io/xiaot-menu/`
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
确保 `server/app.py` 中有以下代码：
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # 允许所有域名访问
```

如果只想允许特定域名访问：
```python
CORS(app, resources={r"/api/*": {"origins": "https://你的用户名.gitee.io"}})
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

**原因**：没有重新拉取 Gitee 代码，或者没有重启 Web 应用

**解决**：
1. 在 PythonAnywhere Bash 中：
```bash
cd ~/xiaot-menu
git pull origin master
```
2. 在 PythonAnywhere Dashboard，**"Web"** → 点击 **"Reload"**

---

## 📝 部署检查清单

- [ ] TiDB Cloud 集群已创建
- [ ] 数据库和表已创建
- [ ] 初始数据已插入
- [ ] Gitee 账号已注册并实名认证
- [ ] 代码已推送到 Gitee
- [ ] PythonAnywhere 账号已注册
- [ ] 后端已部署到 PythonAnywhere
- [ ] 环境变量已配置
- [ ] 前端 `API_BASE` 已修改为生产环境地址
- [ ] 前端已部署到 Gitee Pages
- [ ] TiDB Cloud IP 白名单已配置
- [ ] 前后端能正常通信
- [ ] 用手机测试成功

---

## 🎉 部署完成！

恭喜你！现在你的点菜 App 已经部署到云端了：

- **前端地址**：`https://你的用户名.gitee.io/xiaot-menu/`
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
git pull origin master

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
INSERT INTO dishes (id, name, cat, price, `desc`, gradient, image) 
VALUES ('new_dish', '新菜品', 'soup', 18.00, '好吃的~', 'var(--gradient-orange)', NULL);

-- 删除菜品
DELETE FROM dishes WHERE id = 'new_dish';
```

---

**文档版本**：v1.0  
**最后更新**：2026-06-27  
**作者**：小t的菜单开发团队
