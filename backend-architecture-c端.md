# 小t的菜单 — C端后端架构方案

> 基于 `dist/` 目录真实前端代码设计，只覆盖 C 端用户侧功能。
> 前端对接入口：`dist/data.js`（已预留 4 个 TODO fetch 调用）

---

## 1. 技术栈选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **运行时** | Node.js 22 LTS | 与前端 JS 生态一致，无跨语言沟通成本 |
| **框架** | Express.js | 轻量、生态成熟，适合此规模的项目 |
| **ORM** | Prisma | 类型安全、自动迁移、查询可读性好 |
| **数据库** | PostgreSQL 16 | 关系型数据天然适合菜单/订单场景 |
| **认证** | JWT（bcrypt + jsonwebtoken） | 无状态，前端 SPA 原生支持 |
| **图片存储** | 本地文件系统（预留 S3 切换接口） | 初期简单，通过接口抽象可随时切换 |
| **图片上传** | Multer（multipart） | 菜品图片 < 5MB，multipart 最简方案 |
| **日志** | Winston（结构化 JSON） | 可解析、可过滤、可接入日志平台 |
| **校验** | Joi | 所有输入边界层强制校验 |
| **部署** | 单进程 Node 服务（初期） | 日订单量 500-2000，单进程足够 |

**为什么不选 Microservices？**
项目当前规模下，单体服务更高效：无服务间通信开销、无分布式事务复杂度、运维成本低。当订单量达到日万单级别再拆不迟。

---

## 2. 系统架构图

```
┌──────────────────────────┐
│   静态文件服务器 (Nginx)    │
│   dist/index.html         │
│   dist/data.js            │
│   dist/test_data.js(废弃)  │
└──────────┬───────────────┘
           │ HTTP (JSON)
           ▼
┌──────────────────────────┐
│     Express API Server   │
│                          │
│  ┌────────────────────┐  │
│  │  中间件层           │  │
│  │  helmet / cors     │  │
│  │  rate-limit / auth │  │
│  │  validation (Joi)  │  │
│  └────────┬───────────┘  │
│           │               │
│  ┌────────▼───────────┐  │
│  │   路由层             │  │
│  │  /api/auth          │  │
│  │  /api/chefs         │  │
│  │  /api/dishes        │  │
│  │  /api/categories    │  │
│  │  /api/cart          │  │
│  │  /api/orders        │  │
│  │  /api/user/state    │  │
│  │  /api/uploads       │  │
│  └────────┬───────────┘  │
│           │               │
│  ┌────────▼───────────┐  │
│  │   服务层             │  │
│  │  业务逻辑 + 事务     │  │
│  └────────┬───────────┘  │
│           │               │
│  ┌────────▼───────────┐  │
│  │   数据层 (Prisma)    │  │
│  └────────┬───────────┘  │
└───────────┼──────────────┘
            │
    ┌───────▼───────┐
    │  PostgreSQL   │
    │  (数据库)      │
    └───────────────┘

┌──────────────────┐
│  uploads/ 目录    │
│  (菜品图片)       │
└──────────────────┘
```

---

## 3. 数据库设计

### 3.1 ER 关系

```
users ──1:N── orders ──1:N── order_items ──N:1── dishes
  │                                      │
  │         ┌────────────────────────────┘
  │         ▼
  ├──1:1── user_state ──N:1── chefs
  │
  └──1:N── cart_items ──N:1── dishes

dishes ──N:1── categories
```

### 3.2 完整 DDL

```sql
-- ============================================================
-- 1. 用户表
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,          -- bcrypt
    role            VARCHAR(20)  NOT NULL DEFAULT 'customer'
                        CHECK (role IN ('customer', 'merchant')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. 大厨表（预置数据，不可通过 API 修改）
-- ============================================================
CREATE TABLE chefs (
    id          VARCHAR(20)  PRIMARY KEY,            -- 'lulu' | 'nailong' | 'beini'
    name        VARCHAR(50)  NOT NULL,               -- '水豚噜噜'
    img         VARCHAR(255) NOT NULL,               -- 'assets/images/2_68.png'
    emoji       VARCHAR(10)  NOT NULL,               -- '🐹'
    role_label  VARCHAR(50)  NOT NULL,               -- '汤品专家 🥣'
    tag         VARCHAR(100) NOT NULL,               -- '汤品超好喝~'
    sort_order  INT          NOT NULL DEFAULT 0
);

-- 种子数据
INSERT INTO chefs (id, name, img, emoji, role_label, tag, sort_order) VALUES
  ('lulu',    '水豚噜噜',   'assets/images/2_68.png', '🐹', '汤品专家 🥣', '汤品超好喝~', 1),
  ('nailong', '奶龙',       'assets/images/2_74.png', '🐲', '荤菜大师 🍖', '肉肉超满足~', 2),
  ('beini',   '小恐龙贝尼', 'assets/images/2_80.png', '🦕', '素菜达人 🥬', '素菜超美味~', 3);

-- ============================================================
-- 3. 菜品分类表
-- ============================================================
CREATE TABLE categories (
    key         VARCHAR(10) PRIMARY KEY,             -- 'soup' | 'meat' | 'veg'
    label       VARCHAR(50) NOT NULL,                -- '汤品🥣'
    sort_order  INT NOT NULL DEFAULT 0
);

INSERT INTO categories (key, label, sort_order) VALUES
  ('soup', '汤品🥣', 1),
  ('meat', '荤菜🍖', 2),
  ('veg',  '素菜🥬', 3);

-- ============================================================
-- 4. 菜品表
-- ============================================================
CREATE TABLE dishes (
    id          VARCHAR(50)  PRIMARY KEY,            -- 'fanqiedantang'
    name        VARCHAR(100) NOT NULL,               -- '番茄蛋汤'
    cat         VARCHAR(10)  NOT NULL REFERENCES categories(key),
    price       INT          NOT NULL CHECK (price > 0),
    description TEXT,                                -- '酸甜可口，暖心暖胃~'
    gradient    VARCHAR(100),                        -- 'var(--gradient-orange)'
    image_url   VARCHAR(255),                        -- 菜品图片 URL
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 索引：按分类查活跃菜品（最常见查询）
CREATE INDEX idx_dishes_cat_active ON dishes (cat) WHERE is_active = true;
-- 索引：搜索菜品名
CREATE INDEX idx_dishes_name ON dishes (name);
-- GIN 索引：中文全文搜索
CREATE INDEX idx_dishes_name_trgm ON dishes USING gin (name gin_trgm_ops);

-- 种子数据（对应 test_data.js 的 4 道菜）
INSERT INTO dishes (id, name, cat, price, description, gradient) VALUES
  ('fanqiedantang',   '番茄蛋汤',   'soup', 12, '酸甜可口，暖心暖胃~', 'var(--gradient-orange)'),
  ('dongguapaigutang', '冬瓜排骨汤', 'soup', 22, '清淡鲜美，营养满分',   'var(--gradient-green)'),
  ('chaoniurou',       '炒牛肉',     'meat', 28, '鲜嫩多汁，肉香四溢~', 'var(--gradient-orange)'),
  ('chaokongxincai',   '炒空心菜',   'veg',  16, '清脆爽口，鲜嫩美味~', 'var(--gradient-green)');

-- ============================================================
-- 5. 用户状态表（选中的大厨）
-- ============================================================
CREATE TABLE user_state (
    user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    selected_chef   VARCHAR(20) REFERENCES chefs(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 6. 购物车表
-- ============================================================
CREATE TABLE cart_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dish_id     VARCHAR(50) NOT NULL REFERENCES dishes(id) ON DELETE CASCADE,
    quantity    INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (user_id, dish_id)    -- 同一用户同一菜品只存一条，数量叠加
);

CREATE INDEX idx_cart_user ON cart_items (user_id);

-- ============================================================
-- 7. 订单表
-- ============================================================
CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number    VARCHAR(20)  NOT NULL UNIQUE,     -- 'DD20260627001'
    user_id         UUID         NOT NULL REFERENCES users(id),
    chef_id         VARCHAR(20)  NOT NULL REFERENCES chefs(id),
    dish_total      INT          NOT NULL,            -- 菜品合计金额
    service_fee     INT          NOT NULL DEFAULT 0,  -- 大厨服务费
    grand_total     INT          NOT NULL,            -- 总计
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'confirmed', 'preparing', 'completed', 'cancelled')),
    remark          TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user   ON orders (user_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_number ON orders (order_number);

-- ============================================================
-- 8. 订单明细表
-- ============================================================
CREATE TABLE order_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id    UUID         NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    dish_id     VARCHAR(50)  NOT NULL REFERENCES dishes(id),
    dish_name   VARCHAR(100) NOT NULL,   -- 冗余存储，防止菜品被删后订单信息丢失
    price       INT          NOT NULL,   -- 下单时的单价
    quantity    INT          NOT NULL DEFAULT 1 CHECK (quantity > 0)
);

CREATE INDEX idx_order_items_order ON order_items (order_id);
```

### 3.3 关键设计决策

| 决策 | 理由 |
|------|------|
| 金额用 `INT`（单位：元） | 前端 `price` 是整数，避免浮点精度问题 |
| `order_items.dish_name` 冗余 | 菜品可能被删除或改价，订单快照不能变 |
| `cart_items` 与 `user_state` 分开 | 购物车是高频读写，独立表减少锁竞争 |
| `UNIQUE(user_id, dish_id)` 约束 | 同一菜品加购物车只增加数量，不产生重复行 |
| `gin_trgm_ops` 搜索索引 | 支持中文模糊搜索，`LIKE '%番茄%'` 也能走索引 |

---

## 4. API 接口设计

### 4.1 通用规范

**请求格式：**
- `Content-Type: application/json`（文件上传除外）
- 认证接口需带 `Authorization: Bearer <token>`

**成功响应格式：**
```json
{
  "data": { ... },
  "meta": { "timestamp": "2026-06-27T07:00:00.000Z" }
}
```

**错误响应格式：**
```json
{
  "error": "人类可读的错误描述",
  "code": "ERROR_CODE",
  "details": []  // 可选，表单字段级错误
}
```

**HTTP 状态码约定：**
| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 / Token 过期 |
| 404 | 资源不存在 |
| 409 | 冲突（如重复注册） |
| 422 | 业务逻辑校验不通过（如购物车为空时下单） |
| 429 | 触发频率限制 |
| 500 | 服务器内部错误 |

---

### 4.2 Auth — 认证模块

#### `POST /api/auth/register`
注册新用户。

```
Body:
{
  "username": "zhangsan",        // 必填，3-50字符
  "password": "abc123456"        // 必填，6-100字符
}

Response 201:
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "zhangsan",
    "role": "customer",
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}

Error 409:
{ "error": "用户名已被注册", "code": "USERNAME_TAKEN" }
```

#### `POST /api/auth/login`
登录。

```
Body:
{
  "username": "zhangsan",
  "password": "abc123456"
}

Response 200:
{
  "data": {
    "id": "550e8400...",
    "username": "zhangsan",
    "role": "customer",
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}

Error 401:
{ "error": "用户名或密码错误", "code": "INVALID_CREDENTIALS" }
```

#### `GET /api/auth/me`
获取当前登录用户信息（需认证）。

```
Headers: Authorization: Bearer <token>

Response 200:
{
  "data": {
    "id": "550e8400...",
    "username": "zhangsan",
    "role": "customer"
  }
}
```

---

### 4.3 Chefs — 大厨模块

#### `GET /api/chefs`
获取大厨列表（公开接口）。

```
Response 200:
{
  "data": [
    {
      "id": "lulu",
      "name": "水豚噜噜",
      "img": "assets/images/2_68.png",
      "emoji": "🐹",
      "role": "汤品专家 🥣",
      "tag": "汤品超好喝~"
    },
    { "id": "nailong", ... },
    { "id": "beini", ... }
  ]
}
```

> **与 data.js 对接**：返回格式直接对应 `CHEFS = await fetch('/api/chefs').then(r => r.json()).then(r => r.data)`。

---

### 4.4 Categories — 分类模块

#### `GET /api/categories`
获取菜品分类列表（公开接口）。

```
Response 200:
{
  "data": [
    { "key": "all",  "label": "所有菜品" },
    { "key": "soup", "label": "汤品🥣" },
    { "key": "meat", "label": "荤菜🍖" },
    { "key": "veg",  "label": "素菜🥬" }
  ]
}
```

> 注意：`all` 不是数据库中的分类，前端用它表示"不过滤"。后端在 `/api/dishes?cat=all` 时不加 WHERE 条件即可。

---

### 4.5 Dishes — 菜品模块

#### `GET /api/dishes`
获取菜品列表（公开接口）。支持分类筛选和名称搜索。

```
Query Parameters:
  cat    可选，分类 key（如 'soup'），传 'all' 或省略则不过滤
  search 可选，菜品名称模糊搜索关键词
  page   可选，页码，默认 1
  limit  可选，每页数量，默认 50

Response 200:
{
  "data": [
    {
      "id": "fanqiedantang",
      "name": "番茄蛋汤",
      "cat": "soup",
      "price": 12,
      "desc": "酸甜可口，暖心暖胃~",
      "gradient": "var(--gradient-orange)",
      "image_url": null
    },
    ...
  ],
  "meta": {
    "total": 4,
    "page": 1,
    "limit": 50,
    "timestamp": "2026-06-27T07:00:00.000Z"
  }
}
```

> **与 data.js 对接**：返回格式直接对应 `DISHES = await fetch('/api/dishes').then(r => r.json()).then(r => r.data)`。
> 前端已有分类筛选逻辑，只需把 `cat` 参数拼到 URL 上即可。

#### `GET /api/dishes/:id`
获取单个菜品详情。

```
Response 200:
{
  "data": {
    "id": "fanqiedantang",
    "name": "番茄蛋汤",
    ...
  }
}
```

---

### 4.6 Cart — 购物车模块（需认证）

#### `GET /api/cart`
获取当前用户购物车。

```
Response 200:
{
  "data": {
    "items": [
      {
        "dish_id": "fanqiedantang",
        "name": "番茄蛋汤",
        "price": 12,
        "quantity": 2
      }
    ],
    "total_amount": 24,
    "item_count": 2
  }
}
```

#### `POST /api/cart/items`
添加菜品到购物车。若菜品已在购物车中，则数量叠加。

```
Body:
{
  "dish_id": "fanqiedantang",
  "quantity": 1     // 可选，默认 1
}

Response 201:
{
  "data": {
    "items": [...],
    "total_amount": 24,
    "item_count": 2
  }
}
```

#### `PUT /api/cart/items/:dishId`
更新购物车中某菜品的数量。

```
Body:
{
  "quantity": 3
}

Response 200: { "data": { ... } }
```

#### `DELETE /api/cart/items/:dishId`
从购物车中删除某菜品。

```
Response 200: { "data": { ... } }
```

#### `DELETE /api/cart`
清空购物车。

```
Response 200: { "data": { "items": [], "total_amount": 0, "item_count": 0 } }
```

---

### 4.7 Orders — 订单模块（需认证）

#### `POST /api/orders`
提交购物车结算，创建订单。

```
Body:
{
  "chef_id": "lulu"    // 当前选择的大厨
}

Response 201:
{
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "order_number": "DD20260627001",
    "chef": {
      "id": "lulu",
      "name": "水豚噜噜",
      "emoji": "🐹"
    },
    "items": [
      { "name": "番茄蛋汤", "price": 12, "quantity": 2 }
    ],
    "dish_total": 24,
    "service_fee": 5,
    "grand_total": 29,
    "status": "pending",
    "created_at": "2026-06-27T07:00:00.000Z"
  }
}

Error 422:
{ "error": "购物车为空，无法下单", "code": "EMPTY_CART" }
```

> **订单号规则**：`DD` + `YYYYMMDD` + `3位流水号`。每日从 001 开始，通过数据库序列或 Redis 原子操作生成。

#### `GET /api/orders`
我的订单列表。

```
Query Parameters:
  status    可选，订单状态筛选
  search    可选，按订单号或菜品名搜索
  start_date 可选，起始日期（ISO 8601）
  end_date   可选，结束日期（ISO 8601）
  page      可选，默认 1
  limit     可选，默认 20

Response 200:
{
  "data": [
    {
      "id": "660e8400...",
      "order_number": "DD20260627001",
      "chef_name": "水豚噜噜",
      "chef_emoji": "🐹",
      "status": "pending",
      "item_count": 3,
      "grand_total": 29,
      "created_at": "2026-06-27T07:00:00.000Z"
    }
  ],
  "meta": {
    "total": 25,
    "total_amount": 1580,
    "page": 1,
    "limit": 20,
    "timestamp": "..."
  }
}
```

> **meta.total_amount**：所有匹配订单的总金额，对应前端历史订单页底部的统计栏。

#### `GET /api/orders/:id`
订单详情。

```
Response 200:
{
  "data": {
    "id": "660e8400...",
    "order_number": "DD20260627001",
    "chef": { "id": "lulu", "name": "水豚噜噜", "emoji": "🐹" },
    "items": [
      { "name": "番茄蛋汤", "price": 12, "quantity": 2 },
      { "name": "炒牛肉", "price": 28, "quantity": 1 }
    ],
    "dish_total": 52,
    "service_fee": 5,
    "grand_total": 57,
    "status": "pending",
    "created_at": "2026-06-27T07:00:00.000Z"
  }
}
```

---

### 4.8 User State — 用户状态模块（需认证）

#### `GET /api/user/state`
获取用户当前状态（选中的大厨 + 购物车概要）。

```
Response 200:
{
  "data": {
    "selectedChef": "lulu",
    "cart": [
      { "name": "番茄蛋汤", "price": 12 },
      { "name": "炒牛肉", "price": 28 }
    ]
  }
}
```

> **与 data.js 对接**：返回格式完全对应 `DEFAULT_STATE = await fetch('/api/user/state').then(r => r.json()).then(r => r.data)`。
> `cart` 数组的格式与 `test_data.js` 中的 `defaultState.cart` 保持一致：`{ name, price }[]`。

#### `PUT /api/user/state/chef`
更新用户选中的大厨。

```
Body:
{
  "chef_id": "nailong"
}

Response 200:
{
  "data": {
    "selectedChef": "nailong"
  }
}
```

---

### 4.9 Uploads — 文件上传模块（需认证）

> C 端暂时不需要上传功能，但保留接口供后续 B 端扩展。

#### `POST /api/uploads/dish-image`
上传菜品图片。

```
Content-Type: multipart/form-data
Body: file (字段名 "image")

限制：仅允许 image/jpeg, image/png, image/webp，最大 5MB

Response 201:
{
  "data": {
    "url": "/uploads/dishes/a1b2c3d4-番茄蛋汤.jpg"
  }
}
```

---

### 4.10 接口总览表

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 注册 |
| POST | `/api/auth/login` | 否 | 登录 |
| GET | `/api/auth/me` | 是 | 当前用户信息 |
| GET | `/api/chefs` | 否 | 大厨列表 |
| GET | `/api/categories` | 否 | 分类列表 |
| GET | `/api/dishes` | 否 | 菜品列表（支持搜索/筛选/分页） |
| GET | `/api/dishes/:id` | 否 | 菜品详情 |
| GET | `/api/cart` | 是 | 获取购物车 |
| POST | `/api/cart/items` | 是 | 添加菜品到购物车 |
| PUT | `/api/cart/items/:dishId` | 是 | 更新购物车菜品数量 |
| DELETE | `/api/cart/items/:dishId` | 是 | 删除购物车菜品 |
| DELETE | `/api/cart` | 是 | 清空购物车 |
| POST | `/api/orders` | 是 | 创建订单 |
| GET | `/api/orders` | 是 | 我的订单列表 |
| GET | `/api/orders/:id` | 是 | 订单详情 |
| GET | `/api/user/state` | 是 | 获取用户状态 |
| PUT | `/api/user/state/chef` | 是 | 更新选中大厨 |
| POST | `/api/uploads/dish-image` | 是 | 上传菜品图片 |

---

## 5. 认证与安全方案

### 5.1 JWT 设计

```
Payload:
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",  // user.id
  "role": "customer",
  "iat": 1719475200,
  "exp": 1719561600     // 24 小时后过期
}
```

- 使用 `HS256` 签名，密钥通过环境变量 `JWT_SECRET` 注入
- Token 有效期 24 小时（C 端用户场景，较长有效期提升体验）
- 简化为单 token 模式，不做 refresh token（MVP 阶段复杂度不划算）

### 5.2 安全中间件层

```
Request
  → helmet()           // 安全 HTTP 头 (CSP, X-Frame-Options, etc.)
  → cors()             // 只允许前端域名
  → rateLimit()        // IP 级别限流
  → express.json()     // JSON 解析（限制 1MB）
  → auth (可选)        // JWT 验证
  → validate (Joi)     // 请求体/参数校验
  → Handler
  → errorHandler       // 全局错误处理
```

### 5.3 安全措施清单

| 措施 | 实现 |
|------|------|
| 密码加密 | bcrypt，cost factor = 12 |
| JWT 密钥 | 环境变量注入，长度 ≥ 32 字符 |
| 请求体大小限制 | `express.json({ limit: '1mb' })` |
| CORS | 白名单域名，不允许 `*` |
| 速率限制 | 认证接口：15 分钟内最多 20 次；通用接口：15 分钟 100 次 |
| SQL 注入防护 | Prisma 参数化查询，天然免疫 |
| 输入校验 | 所有入参经 Joi schema 校验 |
| 文件上传限制 | 仅图片类型，最大 5MB |
| 错误信息消毒 | 生产环境不返回堆栈信息 |

---

## 6. 图片上传方案

### 6.1 初期方案（本地存储）

```
POST /api/uploads/dish-image
  → Multer 中间件解析 multipart
  → 校验文件类型（MIME + magic bytes）
  → 生成唯一文件名：{uuid}-{原始名}.{ext}
  → 存储到 /uploads/dishes/
  → 返回可访问 URL

静态文件挂载：
  app.use('/uploads', express.static('uploads'))
```

### 6.2 扩展接口（预留 S3 切换）

```typescript
// 抽象存储接口
interface StorageProvider {
  upload(file: Buffer, key: string, contentType: string): Promise<string>;
  getUrl(key: string): string;
  delete(key: string): Promise<void>;
}

// 本地实现
class LocalStorage implements StorageProvider { ... }

// S3 实现（后续切换只需实现此接口）
class S3Storage implements StorageProvider { ... }
```

切换时只需修改一行依赖注入，业务代码零改动。

---

## 7. 前端对接指南

### 7.1 data.js 改造

当前 `dist/data.js` 的 4 个 TODO 行按如下改造：

```javascript
// 原代码                                      → 改造后

var CHEFS = TEST_DATA.chefs;                   → let CHEFS = [];
                                                  fetch('/api/chefs')
                                                    .then(r => r.json())
                                                    .then(json => CHEFS = json.data);

var DISHES = TEST_DATA.dishes;                 → let DISHES = [];
                                                  fetch('/api/dishes')
                                                    .then(r => r.json())
                                                    .then(json => DISHES = json.data);

var CATEGORIES = TEST_DATA.categories;          → let CATEGORIES = [];
                                                  fetch('/api/categories')
                                                    .then(r => r.json())
                                                    .then(json => CATEGORIES = json.data);

var DEFAULT_STATE = TEST_DATA.defaultState;     → let DEFAULT_STATE = { selectedChef: null, cart: [] };
                                                  fetch('/api/user/state', { headers: authHeader() })
                                                    .then(r => r.json())
                                                    .then(json => DEFAULT_STATE = json.data);
```

### 7.2 需要前端新增的逻辑

当前前端是纯静态演示版，部分功能需要补充 JS 逻辑才能与后端完整对接：

| 功能 | 当前状态 | 需要做的事 |
|------|---------|-----------|
| 登录/注册 | 无 UI | 新增登录页或弹窗，存储 token 到 localStorage |
| 请求认证 | 无 | 封装 `authHeader()` 函数，从 localStorage 读取 token |
| 购物车持久化 | 仅内存 | 调用 `/api/cart` 系列接口同步 |
| 下单 | 静态假数据 | 调用 `POST /api/orders`，用返回数据渲染成功页 |
| 历史订单 | 静态假数据 | 调用 `GET /api/orders`，用返回数据渲染列表 |
| 搜索 | UI 存在但逻辑为空 | 绑定搜索栏输入事件，带 `search` 参数请求 `/api/dishes` |
| 订单号 | 写死 `DD20260627001` | 从 API 响应中读取 |

---

## 8. 项目目录结构

```
server/
├── prisma/
│   ├── schema.prisma             # 数据模型定义
│   ├── migrations/               # 迁移文件（自动生成）
│   └── seed.ts                   # 种子数据（3位大厨 + 4道菜 + 3分类）
├── src/
│   ├── app.ts                    # Express 应用入口
│   ├── config.ts                 # 环境变量集中管理 + 启动校验
│   ├── middleware/
│   │   ├── auth.ts               # JWT 认证中间件
│   │   ├── validate.ts           # Joi 校验中间件工厂
│   │   ├── error-handler.ts      # 全局错误处理
│   │   └── request-id.ts         # 请求 ID 生成与传播
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── auth.controller.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── auth.schema.ts    # Joi 校验 schema
│   │   │   └── auth.routes.ts
│   │   ├── chefs/
│   │   │   ├── chefs.controller.ts
│   │   │   ├── chefs.service.ts
│   │   │   └── chefs.routes.ts
│   │   ├── dishes/
│   │   │   ├── dishes.controller.ts
│   │   │   ├── dishes.service.ts
│   │   │   ├── dishes.schema.ts
│   │   │   └── dishes.routes.ts
│   │   ├── categories/
│   │   │   ├── categories.controller.ts
│   │   │   ├── categories.service.ts
│   │   │   └── categories.routes.ts
│   │   ├── cart/
│   │   │   ├── cart.controller.ts
│   │   │   ├── cart.service.ts
│   │   │   ├── cart.schema.ts
│   │   │   └── cart.routes.ts
│   │   ├── orders/
│   │   │   ├── orders.controller.ts
│   │   │   ├── orders.service.ts
│   │   │   ├── orders.schema.ts
│   │   │   └── orders.routes.ts
│   │   ├── user-state/
│   │   │   ├── user-state.controller.ts
│   │   │   ├── user-state.service.ts
│   │   │   └── user-state.routes.ts
│   │   └── uploads/
│   │       ├── uploads.controller.ts
│   │       ├── uploads.service.ts
│   │       └── uploads.routes.ts
│   ├── shared/
│   │   ├── database.ts           # Prisma client 单例 + 连接池
│   │   ├── errors.ts             # 类型化错误类 (NotFound, Validation, etc.)
│   │   ├── logger.ts             # Winston 结构化日志
│   │   └── response.ts           # 统一响应格式工具函数
│   └── index.ts                  # 服务启动入口（含优雅关闭）
├── uploads/
│   └── dishes/                   # 菜品图片存储目录（.gitignore）
├── .env.example                  # 环境变量模板（提交到 Git）
├── .env                          # 实际环境变量（不提交）
├── package.json
└── tsconfig.json
```

> 采用 **Feature-First** 目录结构——每个模块（auth、chefs、dishes、orders...）自包含 controller + service + schema + routes，方便独立修改和测试。

---

## 9. 部署方案

### 9.1 单机部署（初期）

```
┌──────────────────────────────────┐
│  Ubuntu 22.04 / 2C4G             │
│                                  │
│  ┌────────────┐  ┌───────────┐  │
│  │  Nginx     │  │ PostgreSQL│  │
│  │  :80/:443  │  │  :5432    │  │
│  │            │  │           │  │
│  │ /api/* →   │  └───────────┘  │
│  │ :3000      │                 │
│  │            │                 │
│  │ /* →       │                 │
│  │ dist/      │                 │
│  └─────┬──────┘                 │
│        │                        │
│  ┌─────▼──────┐                 │
│  │ Node.js    │                 │
│  │ (pm2)      │                 │
│  │ :3000      │                 │
│  └────────────┘                 │
└──────────────────────────────────┘
```

### 9.2 Nginx 配置要点

```nginx
server {
    listen 80;
    server_name example.com;

    # 前端静态文件
    location / {
        root /var/www/dist;
        try_files $uri /index.html;
    }

    # 菜品图片
    location /uploads/ {
        alias /var/www/server/uploads/;
        expires 30d;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 9.3 进程管理

```bash
# 使用 pm2 管理 Node 进程
pm2 start dist/index.js --name "xiaot-menu" --instances 2
pm2 save
pm2 startup   # 开机自启
```

### 9.4 数据库备份

```bash
# 每日凌晨 3 点自动备份，保留最近 7 天
0 3 * * * pg_dump -U xiaot xiaot_menu > /backups/xiaot_menu_$(date +\%Y\%m\%d).sql
0 4 * * * find /backups -name "*.sql" -mtime +7 -delete
```

---

## 10. 扩展预留

当前设计为 C 端用户侧，但已预留了 B 端扩展点：

| 扩展方向 | 数据结构预留 | API 预留 |
|---------|-------------|---------|
| 商家管理菜品 | `dishes` 表支持 CRUD（已有） | `POST/PUT/DELETE /api/dishes` |
| 商家管理订单 | `orders` 表的 `status` 状态机 | `PUT /api/orders/:id/status` |
| 订单状态实时推送 | — | SSE endpoint `/api/events` |
| 菜品图片管理 | `dishes.image_url` | `POST /api/uploads/dish-image` |
| 食材清单 | 可派生 `ingredients` 表 | `GET /api/ingredients?order_id=` |
| 多商家 | `dishes.merchant_id` | — |
| 支付集成 | `orders.payment_status` | — |

所有扩展只需加字段、加路由，不破坏现有结构。

---

## 11. 关键业务逻辑伪代码

### 下单流程

```typescript
// orders.service.ts
async createOrder(userId: string, chefId: string): Promise<Order> {
  // 1. 查购物车
  const cartItems = await cartRepo.findByUserId(userId);
  if (cartItems.length === 0) throw new BusinessError('购物车为空', 'EMPTY_CART', 422);

  // 2. 查菜品最新价格（以数据库为准）
  const dishIds = cartItems.map(i => i.dishId);
  const dishes = await dishRepo.findByIds(dishIds);

  // 3. 计算金额
  const items = cartItems.map(ci => {
    const dish = dishes.find(d => d.id === ci.dishId)!;
    return { dishId: dish.id, dishName: dish.name, price: dish.price, quantity: ci.quantity };
  });
  const dishTotal = items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const serviceFee = 5;                              // 大厨服务费固定 5 元
  const grandTotal = dishTotal + serviceFee;

  // 4. 生成订单号
  const orderNumber = await generateOrderNumber();   // DD20260627001

  // 5. 事务：创建订单 + 创建订单明细 + 清空购物车 + 更新用户状态
  const order = await prisma.$transaction(async (tx) => {
    const order = await tx.order.create({
      data: { orderNumber, userId, chefId, dishTotal, serviceFee, grandTotal }
    });
    await tx.orderItem.createMany({
      data: items.map(i => ({ ...i, orderId: order.id }))
    });
    await tx.cartItem.deleteMany({ where: { userId } });
    await tx.userState.upsert({
      where: { userId },
      update: { selectedChef: chefId },
      create: { userId, selectedChef: chefId },
    });
    return order;
  });

  return order;
}
```

### 菜品搜索

```typescript
// dishes.service.ts
async findDishes(filters: { cat?: string; search?: string; page: number; limit: number }) {
  const where: any = { isActive: true };

  // 分类筛选（前端传 'all' 时不加条件）
  if (filters.cat && filters.cat !== 'all') {
    where.cat = filters.cat;
  }

  // 模糊搜索（pg_trgm 中文搜索）
  if (filters.search) {
    where.name = { contains: filters.search, mode: 'insensitive' };
  }

  const [dishes, total] = await Promise.all([
    prisma.dish.findMany({ where, skip: (filters.page - 1) * filters.limit, take: filters.limit }),
    prisma.dish.count({ where }),
  ]);

  return { dishes, total };
}
```

---

## 附录：错误码速查表

| Code | HTTP | 说明 |
|------|------|------|
| `USERNAME_TAKEN` | 409 | 用户名已被注册 |
| `INVALID_CREDENTIALS` | 401 | 用户名或密码错误 |
| `UNAUTHORIZED` | 401 | Token 缺失或无效/过期 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 400 | 请求参数校验失败 |
| `EMPTY_CART` | 422 | 购物车为空时下单 |
| `DISH_NOT_ACTIVE` | 422 | 菜品已下架 |
| `FILE_TOO_LARGE` | 400 | 上传文件超过 5MB |
| `INVALID_FILE_TYPE` | 400 | 上传文件类型不允许 |
| `RATE_LIMITED` | 429 | 触发频率限制 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
