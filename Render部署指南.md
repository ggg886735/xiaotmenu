# Render 后端部署指南

> 将 Flask 后端部署到 Render，连接 TiDB Cloud 数据库，实现云端 API 服务。

---

## 一、准备工作

部署前需要准备好：

1. **GitHub 账号**（代码托管，Render 从此拉取代码）
2. **TiDB Cloud 连接字符串**（见《TiDB 部署指南》）
3. **把项目代码推到 GitHub**

---

## 二、将代码推到 GitHub

### 步骤 1：在 GitHub 创建新仓库

1. 登录 [github.com](https://github.com)
2. 点击右上角 `+` → **"New repository"**
3. 填写：
   - **Repository name**：`xiaot-menu`（随意）
   - **Public/Private**：选 `Private`（私有，免费）
   - **不要**勾选 "Initialize this repository with a README"（保持空仓库）
4. 点击 **"Create repository"**

### 步骤 2：推送代码

在项目根目录执行（替换为你的仓库地址）：

```bash
# 初始化 git（如果还没有）
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "初始化：Flask 后端 + 静态前端"

# 关联远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/<你的用户名>/xiaot-menu.git

# 推送到 GitHub
git push -u origin main
```

---

## 三、在 Render 创建 Web Service

1. 打开 [render.com](https://render.com)，用 GitHub 账号登录
2. 点击 **"New +"** → **"Web Service"**
3. 关联你的 GitHub 仓库（`xiaot-menu`）
4. 填写配置：

| 字段 | 值 |
|------|-----|
| **Name** | `xiaot-menu-api`（随意） |
| **Runtime** | `Python 3` |
| **Region** | `Singapore`（新加坡，国内访问快） |
| **Branch** | `main`（默认） |
| **Build Command** | `pip install -r server/requirements.txt` |
| **Start Command** | `cd server && gunicorn -w 2 -b 0.0.0.0:$PORT app:app` |

5. 展开并填写 **Environment Variables**（环境变量）：

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `mysql://root:<密码>@<host>:4000/xiaot_menu?ssl_verify_cert=true&ssl_verify_identity=true` |
| `PYTHON_VERSION` | `3.13` |

> ⚠️ `DATABASE_URL` 填入你在 TiDB 指南中获取的连接字符串

6. 点击 **"Create Web Service"**

部署过程约 3-5 分钟，完成后 Render 会分配一个免费域名，类似：

```
https://xiaot-menu-api.onrender.com
```

---

## 四、验证部署

部署完成后，在浏览器访问：

```
https://<你的render域名>/api/chefs
```

应返回 JSON 格式的 3 位大厨数据。

也可以在终端测试：

```bash
curl https://<你的render域名>/api/dishes
```

---

## 五、连接前端（重要）

前端 `dist/data.js` 中的 API 地址需要改为 Render 的后端域名。

修改 `dist/data.js`，将所有 `http://localhost:8080` 替换为你的 Render 域名：

```javascript
// 修改前
const API_BASE = 'http://localhost:8080';

// 修改后
const API_BASE = 'https://xiaot-menu-api.onrender.com';
```

> 注意：建议用环境变量或配置文件管理这个地址，避免每次部署都手动改。

---

## 六、常见问题

### Q1：部署失败，日志显示 `pymysql not found`？
- 检查 `server/requirements.txt` 是否包含 `pymysql>=1.1.0`
- 重新部署：Render 控制台 → 你的服务 → **"Manual Deploy"**

### Q2：API 返回 500 错误？
- 查看 Render 日志：服务页面 → **"Logs"** 标签
- 常见原因：`DATABASE_URL` 格式错误，或 TiDB 密码填错

### Q3：免费版访问很慢？
- Render 免费版在 15 分钟无访问后会休眠，首次请求需等待约 30 秒唤醒
- 升级到付费版（$7/月）可避免休眠

### Q4：CORS 错误（前端无法调 API）？
- 本项目的 `app.py` 已配置 `CORS(app, origins=["*"])`，允许所有域名访问
- 生产环境建议改为具体域名：
  ```python
  CORS(app, origins=["https://xiaot-menu.vercel.app"])
  ```

---

## 七、更新代码

每次修改代码后，只需：

```bash
git add .
git commit -m "描述本次修改"
git push
```

Render 会自动检测并重新部署（约 1-2 分钟）。

---

## 八、下一步

后端部署完成后，继续看：
- **《Vercel 前端部署指南》** — 将 `dist/` 部署到 Vercel，并配置 API 代理
