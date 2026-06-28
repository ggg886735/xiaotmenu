# 小t的菜单 — PythonAnywhere 一体化部署指南

> **前置条件**：✅ TiDB Cloud 已配置好  ✅ PythonAnywhere 已注册（用户名：xiaotmenu）
>
> **本方案亮点**：前端 + 后端部署在同一个 PythonAnywhere 上，**不需要 GitHub**，不需要 Gitee，不需要实名认证，没有跨域问题。

---

## 为什么不需要 GitHub？

国内连 GitHub 经常超时，而且 PythonAnywhere 支持直接上传文件。所以我们 **打包 zip → 上传到 PythonAnywhere → 解压** 即可，完全绕过 GitHub。

你的 Flask 后端（`server/app.py`）已经内置了静态文件托管：
- 第 31 行：把 `dist/` 目录设为 Flask 的 `static_folder`
- 第 330-345 行：完整的 SPA 回退逻辑

所以用户访问 `https://xiaotmenu.pythonanywhere.com/` → 直接看到前端页面
API 调用 `/api/chefs` → 同一个域名，**没有跨域问题**

---

## 整体流程

```
1. 上传 zip 包到 PythonAnywhere      （上传文件）
2. 解压 + 装依赖                      （照着复制命令）
3. 配置 Web 应用                      （照着填表单）
4. 访问你的网站，测试功能             （浏览器打开链接）
```

---

## 第一步：上传 zip 包（2 分钟）

### 1.1 找到 zip 文件

在你的电脑上找到这个文件：
```
D:\codebuddy\小t的菜单app\xiaotmenu-deploy.zip
```

### 1.2 上传到 PythonAnywhere

1. 登录 **https://www.pythonanywhere.com/**
2. 点顶部 **Files** 标签
3. 在文件管理器页面，点 **Upload a file** 按钮
4. 选择 `xiaotmenu-deploy.zip` 上传
5. 等待上传完成（约 500KB，很快）

---

## 第二步：解压 + 安装依赖（3 分钟）

### 2.1 打开 Bash 控制台

1. 点顶部 **Consoles** → **Bash**

### 2.2 逐行执行以下命令

```bash
# 解压到 ~/xiaotmenu 目录
mkdir ~/xiaotmenu
cd ~/xiaotmenu
unzip ~/xiaotmenu-deploy.zip

# 确认文件结构
ls -la
ls server/
ls dist/
```

应该看到 `server/` 和 `dist/` 两个目录，`server/` 里有 `app.py`、`db.py`、`wsgi.py` 等。

### 2.3 创建虚拟环境 + 安装依赖

```bash
# 创建虚拟环境
mkvirtualenv --python=/usr/bin/python3.10 xiaot-env

# 进入 server 目录安装依赖
cd ~/xiaotmenu/server
pip install -r requirements.txt
```

看到 `Successfully installed...` 就成功了。

---

## 第三步：配置 Web 应用（5 分钟）

### 3.1 创建 Web 应用

1. 回到 Dashboard，点 **Web** → **Add a new web app**
2. 点 **Next**（跳过自动配置）
3. 选 **Manual configuration**（手动配置）
4. 选 **Python 3.10**
5. 点 **Next** 完成

### 3.2 填写配置

在 Web 配置页面修改以下三项：

| 设置项 | 填入值 |
|--------|--------|
| **Source code** | `/home/xiaotmenu/xiaotmenu/server` |
| **Working directory** | `/home/xiaotmenu/xiaotmenu/server` |
| **Virtual environment** | `/home/xiaotmenu/.virtualenvs/xiaot-env` |

> 注意：目录名是 `xiaotmenu`（不是 `xiaot-menu`），因为 zip 解压到了 `~/xiaotmenu`

### 3.3 编辑 WSGI 文件

1. 在 Web 配置页面找到 **WSGI configuration file**，点链接打开编辑器
2. **全选删除**里面的默认内容
3. **粘贴**以下代码：

```python
import sys
import os

# 项目路径
path = '/home/xiaotmenu/xiaotmenu/server'
if path not in sys.path:
    sys.path.insert(0, path)

# 设置数据库连接环境变量（连接 TiDB Cloud）
os.environ['DATABASE_URL'] = 'mysql://YP1JDV94RDqhUhU.root:9tBGwVWy3RWjqgqF@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/xiaot_menu'

# 导入 Flask 应用（前端+后端一体化）
from wsgi import application
```

4. 点 **Save**

### 3.4 重启并测试

1. 点页面顶部的绿色 **Reload** 按钮
2. 等待 10 秒
3. 打开浏览器访问：**https://xiaotmenu.pythonanywhere.com/**
   - ✅ 看到点菜 App 界面 → **部署完全成功！**
4. 再访问：**https://xiaotmenu.pythonanywhere.com/api/chefs**
   - ✅ 看到 JSON 格式的大厨数据 → **API 正常！**

---

## 第四步：排错

### 报错 1："Internal Server Error"

1. 在 PythonAnywhere 点 **Web** → **Log files** → **Error log**
2. 常见原因：
   - 依赖没装全 → `pip install flask flask-cors pymysql python-dotenv`
   - WSGI 文件路径写错 → 检查路径是否是 `/home/xiaotmenu/xiaotmenu/server`
   - 代码有导入错误 → 看 Error log 里的具体报错

### 报错 2：TiDB Cloud 连接超时

> ⚠️ PythonAnywhere 免费账号可能限制出站 TCP 连接（仅允许 80/443 端口），TiDB Cloud 用 4000 端口可能连不上。

如果 Error log 里看到 `Connection timed out` 或 `Can't connect to MySQL server`：

**告诉我**，我会把数据库连接方式从 MySQL 协议改为 TiDB Cloud HTTP Data API（走 443 端口，不受限制）。

### 报错 3：页面空白 / 404

- 检查 WSGI 文件里 `from wsgi import application` 是否正确
- 检查 Source code 路径是否指向 `server` 目录
- 在 Bash 里确认 `~/xiaotmenu/dist/` 目录有文件：`ls ~/xiaotmenu/dist/`

### 报错 4：页面出来了但没数据

- 打开浏览器 F12 → Console，看有没有报错
- 打开 F12 → Network，看 `/api/chefs` 请求是否返回 200
- 如果 API 返回 500 → 看后端 Error log

---

## 后续：更新代码

以后改了代码，重新打包 zip 上传，然后在 Bash 执行：

```bash
cd ~/xiaotmenu
unzip -o ~/xiaotmenu-deploy.zip
```

然后回到 Web 配置页面点 **Reload** 即可。

---

## 快速检查清单

- [ ] zip 文件上传到 PythonAnywhere
- [ ] Bash 中解压到 ~/xiaotmenu
- [ ] 虚拟环境 + 依赖安装
- [ ] Web 应用创建（Manual + Python 3.10）
- [ ] Source code 路径：`/home/xiaotmenu/xiaotmenu/server`
- [ ] WSGI 文件编辑（粘贴代码）
- [ ] Reload
- [ ] 访问 `https://xiaotmenu.pythonanywhere.com/` 看到点菜界面
- [ ] 访问 `/api/chefs` 看到 JSON 数据
