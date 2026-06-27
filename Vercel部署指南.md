# Vercel 前端部署指南

> 将 `dist/` 静态文件部署到 Vercel，并配置 API 代理，让前端能调用 Render 后端。

---

## 一、准备工作

1. **GitHub 账号**（代码已推到 GitHub，见《Render 部署指南》）
2. **Render 后端域名**（后端已部署，拿到 `https://xxx.onrender.com`）
3. **Vercel 账号**（用 GitHub 登录，自动关联仓库）

---

## 二、在 Vercel 创建项目

1. 打开 [vercel.com](https://vercel.com)，用 **GitHub 账号**登录
2. 点击 **"Add New..."** → **"Project"**
3. 选择你的 GitHub 仓库（`xiaot-menu`），点击 **"Import"**
4. 填写配置：

| 字段 | 值 |
|------|-----|
| **Project Name** | `xiaot-menu`（随意） |
| **Framework Preset** | `Other`（纯静态，不用框架） |
| **Root Directory** | `dist`（重要！只部署 dist 目录） |
| **Build Command** | 留空（不需要构建） |
| **Output Directory** | `.`（dist 目录下的所有文件） |

5. 点击 **"Deploy"**

约 30 秒后，Vercel 会分配一个免费域名：

```
https://xiaot-menu.vercel.app
```

---

## 三、配置 API 代理（解决跨域问题）

前端在 `xiaot-menu.vercel.app`，后端在 `xxx.onrender.com`，不同域名会产生 CORS 问题。

**解决方案：在 Vercel 配置反向代理，让 `/api/*` 转发到后端。**

在项目根目录创建 `vercel.json`：

```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://<你的render域名>/api/$1"
    }
  ]
}
```

> 替换 `<你的render域名>` 为实际的 Render 后端地址（不需要 `https://` 前缀以外的路径）

**示例：**

如果 Render 后端域名是 `https://xiaot-menu-api.onrender.com`，则：

```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://xiaot-menu-api.onrender.com/api/$1"
    }
  ]
}
```

---

## 四、修改前端 API 地址

为了让前端在本地和云端都能正常工作，修改 `dist/data.js`，自动适配环境：

```javascript
// dist/data.js 顶部添加：

const API_BASE = location.hostname === 'localhost' || location.hostname === '127.0.0.1'
  ? 'http://localhost:8080'       // 本地开发
  : '';                              // 生产环境：相对路径（走 Vercel 代理）
```

然后确保所有 `fetch` 调用使用 `API_BASE + '/api/...'` 格式。

---

## 五、重新部署

修改完 `vercel.json` 和 `data.js` 后，推送代码：

```bash
git add .
git commit -m "配置 Vercel 代理 + 前端 API 自适应"
git push
```

Vercel 会自动重新部署（约 30 秒）。

---

## 六、验证部署

部署完成后，在浏览器访问：

```
https://xiaot-menu.vercel.app
```

应正常显示「小t的菜单」首页，且：
- 大厨列表能加载
- 菜品列表能加载
- 新增/编辑/删除菜品能正常工作

---

## 七、自定义域名（可选）

如果想用自己的域名（如 `menu.example.com`）：

1. 在 Vercel 项目页面，点击 **"Settings"** → **"Domains"**
2. 输入你的域名，点击 **"Add"**
3. 按提示在你的域名服务商处添加 Vercel 提供的 DNS 记录

---

## 八、常见问题

### Q1：Vercel 部署后页面空白？
- 检查 `Root Directory` 是否填了 `dist`
- 检查 `dist/index.html` 是否存在

### Q2：API 调用失败（502/504）？
- 检查 `vercel.json` 中的 Render 域名是否正确
- 检查 Render 后端是否正常运行（访问 Render 域名直接测试）

### Q3：CORS 错误仍然存在？
- 确认 `vercel.json` 的 rewrite 规则已生效（查看 Vercel 部署日志）
- 或者：在 `app.py` 中把 `CORS(app, origins=["*"])` 改为具体域名

### Q4：Vercel 免费额度够用吗？
- 完全够用：100GB 带宽/月，个人使用完全够

---

## 九、完整部署架构

```
         浏览器（手机 A）    浏览器（手机 B）
               |                  |
               ▼                  ▼
        ┌────────────────────────────────┐
        │  Vercel（前端静态文件）          │
        │  xiaot-menu.vercel.app       │
        └────────────┬─────────────────┘
                     │ /api/* 代理
                     ▼
        ┌────────────────────────────────┐
        │  Render（Flask 后端 API）       │
        │  xiaot-menu-api.onrender.com │
        └────────────┬─────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  TiDB Cloud Serverless（MySQL） │
        │  25GB 免费存储，数据持久化       │
        └────────────────────────────────┘
```

---

## 十、下一步

部署完成后，你可以继续扩展功能：
- **用户注册/登录**（JWT 认证）
- **订单系统**（下单、支付、订单管理）
- **实时通知**（商家端新订单提醒）
- **图片云端存储**（TiDB 只存 URL，图片存到云存储）
