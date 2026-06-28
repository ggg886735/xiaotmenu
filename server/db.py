# ═══════════════════════════════════════════════════════
#  小t的菜单 — 数据库层（SQLite 本地 / MySQL云端 双模式）
#
#  切换方式：设置环境变量 DATABASE_URL，或在 server/.env 中配置
#    ▸ 未设置          → 使用 SQLite (本地开发)
#    ▸ mysql://...     → 使用 MySQL / TiDB Cloud
#
#  server/.env 格式：
#    DATABASE_URL=mysql://<user>:<password>@<host>:4000/<database>
# ═══════════════════════════════════════════════════════

import os
import re
import json
import sqlite3

# ────────────────────────────────────────────────────────
#  加载 .env 文件（如果存在）
# ────────────────────────────────────────────────────────
def _load_env_file(env_path):
    """从 .env 文件加载环境变量到 os.environ"""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                # 只设置尚未存在的变量（命令行环境变量优先）
                if key not in os.environ:
                    os.environ[key] = val


_load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ────────────────────────────────────────────────────────
#  尝试导入 PyMySQL（MySQL / TiDB 驱动）
# ────────────────────────────────────────────────────────
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "data.db")
TEST_DATA_PATH = os.path.join(BASE_DIR, "..", "dist", "test_data.js")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


# ────────────────────────────────────────────────────────
#  DBConnection 包装器
#  sqlite3.Connection 不允许设置自定义属性，用此类包装。
# ────────────────────────────────────────────────────────

class DBConnection:
    def __init__(self, raw_conn, db_type):
        self._raw    = raw_conn
        self._db_type = db_type   # "mysql" | "sqlite"

    @property
    def db_type(self):
        return self._db_type

    def cursor(self, *a, **kw):
        return self._raw.cursor(*a, **kw)

    def commit(self):
        return self._raw.commit()

    def close(self):
        return self._raw.close()

    def execute(self, sql, params=()):
        return self._raw.execute(sql, params)

    def executemany(self, sql, params_seq):
        return self._raw.executemany(sql, params_seq)

    def executescript(self, sql):
        return self._raw.executescript(sql)


def _is_mysql():
    return DATABASE_URL.startswith("mysql://") and not _FALLBACK_TO_SQLITE


def get_db_type():
    if _FALLBACK_TO_SQLITE:
        return "sqlite"
    return "mysql" if _is_mysql() else "sqlite"


def _find_ssl_ca():
    """自动查找系统 CA 证书路径（兼容 Linux / macOS / Windows）"""
    candidates = [
        "/etc/ssl/certs/ca-certificates.crt",   # Debian/Ubuntu (PythonAnywhere)
        "/etc/pki/tls/certs/ca-bundle.crt",      # RHEL/CentOS
        "/etc/ssl/cert.pem",                      # macOS
        "/usr/local/share/certs/ca-root-nss.crt", # FreeBSD
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


# 全局降级标志：MySQL 连接失败后自动切换到 SQLite
_FALLBACK_TO_SQLITE = False


def get_db():
    global _FALLBACK_TO_SQLITE

    if _is_mysql() and not _FALLBACK_TO_SQLITE:
        if not HAS_PYMYSQL:
            raise RuntimeError(
                "TiDB/MySQL 模式需要 PyMySQL 库，请执行：pip install pymysql"
            )
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)

        # TiDB Cloud Serverless 要求 SSL 连接
        ssl_ca = _find_ssl_ca()
        ssl_params = {}
        if ssl_ca:
            ssl_params = {"ssl": {"ca": ssl_ca}}

        try:
            raw = pymysql.connect(
                host=parsed.hostname or "127.0.0.1",
                port=parsed.port or 4000,
                user=parsed.username or "root",
                password=parsed.password or "",
                database=parsed.path.lstrip("/"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
                **ssl_params,
            )
            return DBConnection(raw, "mysql")
        except Exception as e:
            # 连接失败 → 自动降级到 SQLite（PythonAnywhere 等平台可能封禁非标准端口）
            print(f"[db] WARNING: MySQL/TiDB 连接失败 ({e})")
            print("[db] 自动降级为 SQLite 模式（数据将保存在本地 data.db 文件）")
            _FALLBACK_TO_SQLITE = True

    # SQLite 降级模式 / 默认本地模式
    raw = sqlite3.connect(DB_PATH)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return DBConnection(raw, "sqlite")


def close_db(conn):
    if conn:
        try:
            conn.close()
        except Exception:
            pass


# ────────────────────────────────────────────────────────
#  SQL 方言翻译：将 ? 占位符转为对应方言
# ────────────────────────────────────────────────────────

def _translate_sql(sql, db_type):
    if db_type == "mysql":
        return sql.replace("?", "%s")
    return sql


# ────────────────────────────────────────────────────────
#  统一查询接口（返回 [dict, ...]，与方言无关）
# ────────────────────────────────────────────────────────

def fetch_all(conn, sql, params=()):
    db_type = conn.db_type
    sql = _translate_sql(sql, db_type)
    cur = conn.cursor()
    cur.execute(sql, params)
    if db_type == "mysql":
        rows = cur.fetchall()   # list[dict]
    else:
        rows = [dict(r) for r in cur.fetchall()]  # sqlite3.Row → dict
    cur.close()
    return rows


def fetch_one(conn, sql, params=()):
    db_type = conn.db_type
    sql = _translate_sql(sql, db_type)
    cur = conn.cursor()
    cur.execute(sql, params)
    if db_type == "mysql":
        row = cur.fetchone()   # dict | None
    else:
        row = cur.fetchone()
        row = dict(row) if row else None
    cur.close()
    return row


def execute(conn, sql, params=()):
    db_type = conn.db_type
    sql = _translate_sql(sql, db_type)
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def commit(conn):
    try:
        conn.commit()
    except Exception:
        pass


# ────────────────────────────────────────────────────────
#  建表 DDL（按方言分别定义）
#  注意：MySQL/TiDB 用 desc_text 和 key_name 避免保留字冲突
# ────────────────────────────────────────────────────────

DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS chefs (
    id          TEXT PRIMARY KEY,
    name        TEXT    NOT NULL,
    img         TEXT    NOT NULL DEFAULT '',
    emoji       TEXT    NOT NULL DEFAULT '',
    role        TEXT    NOT NULL DEFAULT '',
    tag         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS categories (
    "key" TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dishes (
    id         TEXT PRIMARY KEY,
    name       TEXT    NOT NULL,
    cat        TEXT    NOT NULL DEFAULT 'veg',
    price      INTEGER NOT NULL DEFAULT 0,
    "desc"     TEXT    NOT NULL DEFAULT '',
    gradient   TEXT    NOT NULL DEFAULT 'var(--gradient-orange)',
    image      TEXT             DEFAULT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS user_state (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    selected_chef TEXT    NOT NULL DEFAULT 'lulu',
    cart_json     TEXT    NOT NULL DEFAULT '[]'
);

INSERT OR IGNORE INTO user_state (id, selected_chef, cart_json)
VALUES (1, 'lulu', '[]');
"""

DDL_MYSQL = """
CREATE TABLE IF NOT EXISTS chefs (
    id          VARCHAR(64) PRIMARY KEY,
    name        VARCHAR(128) NOT NULL,
    img         TEXT,
    emoji       VARCHAR(16),
    role        VARCHAR(64),
    tag         VARCHAR(128)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS categories (
    key_name   VARCHAR(32) PRIMARY KEY,
    label   VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dishes (
    id         VARCHAR(64) PRIMARY KEY,
    name       VARCHAR(128) NOT NULL,
    cat        VARCHAR(16),
    price      INTEGER       NOT NULL DEFAULT 0,
    desc_text  TEXT,
    gradient   VARCHAR(64),
    image      TEXT,
    created_at DATETIME      NOT NULL DEFAULT NOW(),
    updated_at DATETIME      NOT NULL DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_state (
    id            INT PRIMARY KEY DEFAULT 1,
    selected_chef VARCHAR(64),
    cart_json     TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO user_state (id, selected_chef, cart_json)
VALUES (1, 'lulu', '[]');
"""


def init_db():
    conn = get_db()
    db_type = conn.db_type
    ddl = DDL_MYSQL if db_type == "mysql" else DDL_SQLITE

    if db_type == "mysql":
        for stmt in _split_sql(ddl):
            if stmt.strip():
                execute(conn, stmt)
    else:
        conn.executescript(ddl)

    commit(conn)
    close_db(conn)
    print(f"[db] Database initialized ({db_type})")


def _split_sql(ddl):
    stmts = []
    cur = []
    for line in ddl.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        cur.append(line)
        if line.endswith(";"):
            stmts.append(" ".join(cur))
            cur = []
    return stmts


# ────────────────────────────────────────────────────────
#  种子数据 — 从 test_data.js 导入初始数据
# ────────────────────────────────────────────────────────

def _parse_js_object(js_obj):
    js_obj = re.sub(r"//[^\n]*", "", js_obj)
    js_obj = re.sub(r"/\*.*?\*/", "", js_obj, flags=re.DOTALL)
    js_obj = re.sub(r"([{,\s])\s*(\w+)\s*:", r'\1"\2":', js_obj)
    js_obj = re.sub(r"'ESC_([^']*)'", r'"\1"', js_obj)
    js_obj = re.sub(r"'([^']*)'", r'"\1"', js_obj)
    js_obj = re.sub(r",\s*([}\]])", r"\1", js_obj)
    return json.loads(js_obj)


def seed_from_test_data():
    if not os.path.exists(TEST_DATA_PATH):
        return

    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"var\s+TEST_DATA\s*=\s*(\{.*?\});", content, re.DOTALL)
    if not match:
        return

    td   = _parse_js_object(match.group(1))
    conn = get_db()
    is_mysql = conn.db_type == "mysql"

    # 列名映射：MySQL 用 desc_text / key_name；SQLite 用 `desc` / `key`
    cat_key_col = "key_name" if is_mysql else "`key`"
    dish_desc_col = "desc_text" if is_mysql else "`desc`"

    # 大厨
    for chef in td.get("chefs", []):
        exists = fetch_one(conn, f"SELECT id FROM chefs WHERE id = ?", (chef["id"],))
        if not exists:
            execute(conn,
                "INSERT INTO chefs (id, name, img, emoji, role, tag) VALUES (?, ?, ?, ?, ?, ?)",
                (chef["id"], chef["name"],
                 chef.get("img", ""),
                 chef.get("emoji", ""),
                 chef.get("role", ""),
                 chef.get("tag", "")))

    # 分类
    for cat in td.get("categories", []):
        exists = fetch_one(conn, f"SELECT {cat_key_col} FROM categories WHERE {cat_key_col} = ?", (cat["key"],))
        if not exists:
            execute(conn,
                f"INSERT INTO categories ({cat_key_col}, label) VALUES (?, ?)",
                (cat["key"], cat["label"]))

    # 菜品（跳过已存在的）
    seeded = 0
    for dish in td.get("dishes", []):
        exists = fetch_one(conn, "SELECT id FROM dishes WHERE id = ?", (dish["id"],))
        if exists:
            continue
        now = _now_str(is_mysql)
        execute(conn,
            f"INSERT INTO dishes (id, name, cat, price, {dish_desc_col}, gradient, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (dish["id"], dish["name"], dish["cat"],
             dish["price"], dish.get("desc", ""),
             dish.get("gradient", ""), now, now))
        seeded += 1

    commit(conn)
    close_db(conn)
    seeded_str = f"{seeded} new dish(es)" if seeded > 0 else "(all already exist)"
    print(f"[seed] {len(td.get('chefs', []))} chefs, "
          f"{len(td.get('categories', []))} cats, "
          f"{seeded_str}")


def _now_str(is_mysql):
    from datetime import datetime
    if is_mysql:
        return None   # 由数据库 DEFAULT NOW() 处理
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ────────────────────────────────────────────────────────
#  启动时自动初始化
# ────────────────────────────────────────────────────────

if __name__ != "__main__":
    init_db()
    seed_from_test_data()
