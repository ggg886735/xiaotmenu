# 小t的菜单 — Railway 部署指南（小白版）

> 适用人群：没有云服务器运维经验，想把自己做的 App 部署到公网上让任何人都能访问。
> 预计时间：20~30 分钟完成全部步骤。

---

## 一、部署前你需要什么

| 物品 | 是否必须 | 说明 |
|------|---------|------|
| GitHub 账号 + 代码已上传 | ✅ 必须 | 你的代码已经在 GitHub 上了，这步已完成 |
| Railway 账号 | ✅ 必须 | 免费注册，免费额度够个人项目用 |
| （可选）TiDB Cloud 账号 | ⭕ 推荐 | 免费 MySQL 云端数据库，数据持久化 |

---

## 二、Railway 是什么？为什么选它？

Railway 是一个**云应用托管平台**，特点：
- 🚀 **直接连 GitHub**：推代码 = 自动部署，不需要手动上传文件
- 💰 **有免费额度**：个人小项目基本够用（每月 $5 免费额度）
- 🛠 **零服务器维护**：不需要懂 Linux、Nginx、Docker
- 📦 **内置 MySQL 插件**：一键添加数据库

---

## 三、步骤一：注册并登录 Railway

1. 打开 👉 [https://railway.app](https://railway.app)
2. 点击 **"Start a Project"**
3. 选择 **"Login with GitHub"**（用 GitHub 账号登录，授权 Railway 访问你的仓库）
4. 登录成功后，你会看到 Railway 的控制台页面

---

## 四、步骤二：创建新项目（从 GitHub 导入）

1. 在 Railway 控制台，点击 **"New Project"**
2. 选择 **"Deploy from GitHub repo"**
3. 在弹出的仓库列表中，找到并选择你的 **小t的菜单 App 的仓库**
   - 如果看不到仓库，点 "Configure GitHub App" 去授权更多仓库
4. 选中仓库后，Railway 会自动开始**第一次部署**（别急，先等它失败也可以，我们要先配置环境变量）

---

## 五、步骤三：配置环境变量（重点！）

部署需要两个关键环境变量，不配置的话 App 能跑，但**数据库是临时的**（重启后数据丢失）。

在 Railway 项目页面：

1. 点击你刚创建的项目（进入项目详情）
2. 点击顶部的 **"Variables"** 标签页
3. 点击 **"New Variable"**，逐个添加以下变量：

### 必配变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `PORT` | _不用手动填_ | Railway 自动设置，我们的 `Procfile` 会自动读取 |

### 数据库选择（二选一）

#### 方案 A：使用 Railway 内置 MySQL（推荐小白）

1. 在项目页面，点击 **"New"** → 选择 **"Database"** → 选择 **"MySQL"**
2. Railway 会自动创建一个 MySQL 数据库，并自动设置 `DATABASE_URL` 环境变量（直接注入到你的 App 服务里，不需要手动填）
3. 等 MySQL 数据库状态变成 **"Active"**（约 1 分钟）
4. 这样就完成了！你的 App 会自动重启并使用这个 MySQL 数据库

#### 方案 B：使用 TiDB Cloud（免费，适合已有账号的用户）

1. 注册 [TiDB Cloud](https://tidbcloud.com)（免费额度）
2. 创建一个 **TiDB Serverless** 集群
3. 获取连接字符串，格式类似：
   ```
   mysql://root:你的密码@你的主机名:4000/xiaot_menu?ssl_mode=REQUIRED
   ```
4. 在 Railway 的 Variables 页面，添加：
   - Name: `DATABASE_URL`
   - Value: 上面的连接字符串

> ✅ 你的代码已经支持这两种方式！`db.py` 会自动检测 `DATABASE_URL` 并切换数据库模式。

---

## 六、步骤四：确认部署配置

Railway 会通过以下文件识别如何启动你的 App（**我已经帮你生成好了**）：

```
你的项目根目录/
├── requirements.txt   ← Railway 读取这个，安装 Python 依赖
├── Procfile           ← Railway 读取这个，知道如何启动 App
└── railway.json       ← 可选的 Railway 配置文件
```

### 检查部署日志

1. 在项目页面，点击你的 **App 服务**（不是 MySQL）
2. 点击 **"Deployments"** 标签页
3. 点击最新的部署记录，查看 **"Build Logs"** 和 **"Deploy Logs"**
4. 如果看到类似这样的日志，说明启动成功：

```
[x] Build completed successfully
[x] App started
    xiaot-menu backend starting...
    DB mode : MYSQL   ← 如果配了 DATABASE_URL
    Address: http://localhost:xxxxx
```

---

## 七、步骤五：获取你的公网访问地址

1. 在项目页面（概览页），找到 **"App"** 服务卡片
2. 右上角会有一个 **公开的 URL**，类似：
   ```
   https://你的项目名-production.up.railway.app
   ```
3. 点击这个链接，就能访问你的 App 了！🎉

> 也可以自定义域名：Settings → Domains → Add Custom Domain

---

## 八、步骤六：验证部署是否成功

打开浏览器，访问：

```
https://你的项目名-production.up.railway.app
```

你应该能看到小t的菜单首页。

再测试一下 API 是否正常（在浏览器地址栏输入）：

```
https://你的项目名-production.up.railway.app/api/chefs
```

如果返回 JSON 数据（大厨列表），说明后端也正常工作！

---

## 九、常见问题 & 故障排查

### ❌ 部署失败："No requirements.txt found"
**原因**：Railway 没找到 `requirements.txt`
**解决**：确认项目根目录有 `requirements.txt`（我已经帮你创建好了）

### ❌ 部署成功但访问 404 / 502
**原因**：端口绑定错误
**解决**：确认 `Procfile` 里有 `$PORT`（不是写死的 8080）

### ❌ 数据库错误："disk I/O error"（SQLite 问题）
**原因**：Railway 的文件系统是临时的，SQLite 数据库文件重启后会丢失
**解决**：按本文「步骤三」配置 MySQL 或 TiDB Cloud

### ❌ 图片上传后刷新就消失了
**原因**：`server/uploads/` 目录在 Railway 上是临时的
**解决**：这是已知限制。生产环境建议接入云存储（如 Cloudinary、AWS S3）
**临时方案**：接受这个问题，或只使用外链图片

### ❌ 每次 git push 后 App 没有自动更新
**原因**：没有开启自动部署
**解决**：在项目 Settings → Deploy → 确认 "Auto Deploy" 是开启的

---

## 十、后续维护

### 更新代码（以后每次改完代码）
```bash
git add .
git commit -m "描述你的改动"
git push
```
Railway 会自动检测并重新部署，约 1~2 分钟生效。

### 查看运行日志
Railway 项目 → 你的 App 服务 → **"Logs"** 标签页

### 回滚到上一个版本
Railway 项目 → **"Deployments"** → 找到想恢复的版本 → 点击 **"Rollback"**

---

## 十一、我能帮你做什么 & 你要自己做什么

### ✅ 我已经帮你做好的（本指南附带的文件）
- ✅ 生成了根目录 `requirements.txt`（Railway 必须）
- ✅ 生成了 `Procfile`（告诉 Railway 如何启动 App）
- ✅ 生成了 `railway.json`（Railway 部署配置）
- ✅ 你的代码本来就支持 MySQL 云端数据库（不需要改代码）

### 🫵 你需要自己手动做的
- 🔐 注册 Railway 账号（需要 GitHub 登录）
- 📦 在 Railway 上创建项目并连接 GitHub 仓库
- 🛠 在 Railway 控制台配置环境变量（MySQL 或 TiDB）
- 🌐 获取并分享你的公网访问地址

### 🤖 我可以继续帮你的
- 如果部署过程中遇到报错，把错误日志发给我，我帮你分析
- 帮你接入 Cloudinary 或其他图床，解决图片上传丢失问题
- 帮你配置自定义域名
- 帮你优化代码，适配生产环境（CORS 限制、安全头等）

---

## 附录：文件清单（我已生成）

```
D:\codebuddy\小t的菜单app\
├── requirements.txt    ← 新建（Railway 构建依赖）
├── Procfile            ← 新建（启动命令）
├── railway.json        ← 新建（Railway 配置）
└── RAILWAY_DEPLOY_GUIDE.md  ← 本文件
```

---

_祝部署顺利！有问题随时找我 🍳_
