# TiDB Cloud Serverless 注册与建库指南

> 适用场景：将「小t的菜单」的数据库部署到云端，实现多手机共享数据、数据持久化不丢失。

---

## 一、注册 TiDB Cloud 账号

1. 打开 [https://tidbcloud.com](https://tidbcloud.com)，点击 **"Get Started for Free"**
2. 选择注册方式（推荐用 GitHub 或 Google 账号登录，更快）
3. 填写基本信息，完成注册

---

## 二、创建 Serverless 集群（免费）

1. 登录后，点击 **"Create Cluster"**
2. 选择 **"Serverless"**（免费层）
3. 配置：
   - **Cluster Name**：`xiaot-menu-db`（随意）
   - **Cloud Provider**：选 `AWS`（节点在新加坡/东京，国内访问较快）
   - **Region**：选 `Tokyo` 或 `Singapore`（延迟更低）
   - **Row Size Limit**：默认 6MB（够用）
4. 点击 **"Create"**，等待集群创建（约 30 秒）

---

## 三、获取连接字符串

集群创建完成后：

1. 在集群详情页，点击 **"Connect"** 按钮
2. 在弹出窗口中：
   - **Connection Type**：选择 `General`
   - **Branch**：选 `main`（默认分支）
   - **Password**：点击 **"Generate Password"** 生成随机密码（复制保存好！）
3. 复制连接字符串，格式类似：

```
mysql://root:<password>@tidb-xxxx.shared.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true
```

> ⚠️ 注意：TiDB Serverless **必须使用 SSL 连接**，连接字符串里会包含 `ssl_verify_cert=true`

---

## 四、创建数据库

用任意 MySQL 客户端连接后，执行：

```sql
CREATE DATABASE IF NOT EXISTS xiaot_menu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

**方式 A：用 TiDB Cloud 自带的 Web SQL 编辑器**
1. 在集群详情页，点击 **"Playground"** 或 **"SQL Editor"**
2. 输入上面的 `CREATE DATABASE` 语句，点击运行

**方式 B：用 pymysql 脚本**
```python
import pymysql
conn = pymysql.connect(
    host="tidb-xxxx.shared.aws.tidbcloud.com",
    port=4000,
    user="root",
    password="<你的密码>",
    database="test",
    ssl={"ca": None},   # Serverless 需要 SSL
)
cur = conn.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS xiaot_menu")
cur.close()
conn.close()
```

创建后，连接字符串中的数据库名改为 `xiaot_menu`：

```
mysql://root:<password>@tidb-xxxx.shared.aws.tidbcloud.com:4000/xiaot_menu?ssl_verify_cert=true&ssl_verify_identity=true
```

---

## 五、建表（首次部署后端时自动完成）

后端启动时会自动执行建表 SQL（`server/db.py` 中的 `init_db()`），**你不需要手动建表**。

只需确保：
1. 数据库 `xiaot_menu` 已创建
2. 连接字符串正确（用户名/密码/主机/端口/数据库名）
3. 后端首次启动时能连通 TiDB

---

## 六、连接字符串格式说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `mysql://` | 协议（固定） | `mysql://` |
| `user` | 用户名（默认 root） | `root` |
| `password` | 第 三 步生成的密码 | `xxxxxxxx` |
| `host` | TiDB 主机地址 | `tidb-xxxx.shared.aws.tidbcloud.com` |
| `port` | 端口（TiDB 固定 4000） | `4000` |
| `database` | 数据库名 | `xiaot_menu` |
| 查询参数 | SSL 配置（Serverless 必须） | `?ssl_verify_cert=true&ssl_verify_identity=true` |

---

## 七、常见问题

### Q1：连接超时？
- 检查连接字符串中的主机名和端口是否正确
- TiDB Serverless 空闲后会暂停，首次请求可能需要 10-30 秒唤醒（正常现象）

### Q2：SSL 错误？
- 确保连接字符串包含 `?ssl_verify_cert=true&ssl_verify_identity=true`
- PyMySQL 连接时需加 `ssl={"ca": None}` 参数（本项目的 `db.py` 已处理）

### Q3：免费额度够用吗？
- 25GB 存储，对点菜 App 完全够用（菜品数据 1 万条以内 < 10MB）
- 每天请求数有限制，但个人使用完全够

---

## 八、下一步

拿到连接字符串后，继续看：
- **《Render 后端部署指南》** — 将 Flask 后端部署到 Render，并配置 `DATABASE_URL` 环境变量
- **《Vercel 前端部署指南》** — 将 `dist/` 静态文件部署到 Vercel
