# ═══════════════════════════════════════════════════════
#  小t的菜单 — 后端服务 (Flask)
#
#  启动方式：
#    ▸ 本地开发：python app.py
#    ▸ 生产部署：gunicorn -w 2 -b 0.0.0.0:$PORT app:app
#
#  数据库切换：
#    ▸ server/.env 中设置 DATABASE_URL → TiDB Cloud / MySQL (云端)
#    ▸ 未设置                          → SQLite (本地开发)
#
#  访问地址：http://localhost:8080
# ═══════════════════════════════════════════════════════

import os
import uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from db import (
    get_db, close_db,
    fetch_all, fetch_one, execute, commit,
    get_db_type,
)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "..", "dist"),
    static_url_path="",
)
CORS(app, origins=["*"])   # 部署后可将 "*" 改为前端域名

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ────────────────────────────────────────────────────────
#  工具函数
# ────────────────────────────────────────────────────────

def make_response(data, status_code=200):
    return jsonify({
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }), status_code


def _is_mysql():
    return get_db_type() == "mysql"


# 列名映射（MySQL 用 desc_text / key_name；SQLite 用 `desc` / `key`）
# 通过 SELECT 别名统一返回给前端
_COL_CAT_KEY = "key_name AS key"     if _is_mysql() else "`key`"
_COL_DISH_DESC = "desc_text AS `desc`" if _is_mysql() else "`desc`"
COL_CAT_KEY = _COL_CAT_KEY
COL_DISH_DESC = _COL_DISH_DESC


# ────────────────────────────────────────────────────────
#  API — 大厨 & 分类（只读）
# ────────────────────────────────────────────────────────

@app.route("/api/chefs")
def get_chefs():
    conn = get_db()
    rows = fetch_all(conn, "SELECT id, name, img, emoji, role, tag FROM chefs")
    close_db(conn)
    return make_response(rows)


@app.route("/api/categories")
def get_categories():
    conn = get_db()
    is_m = _is_mysql()
    # TiDB 用 key_name 列，SQLite 用 `key` 列
    col_key = "key_name" if is_m else "key"
    rows = fetch_all(conn, f"SELECT {col_key}, label FROM categories")
    normalized = []
    for r in rows:
        k = r.get("key") or r.get("key_name", "")
        normalized.append({"key": k, "label": r["label"]})
    close_db(conn)
    return make_response(normalized)


# ────────────────────────────────────────────────────────
#  API — 菜品 CRUD
# ────────────────────────────────────────────────────────

@app.route("/api/dishes", methods=["GET", "POST"])
def dishes_collection():
    if request.method == "GET":
        conn = get_db()
        cat    = request.args.get("cat", "all")
        search = request.args.get("search", "").strip()

        sql  = f"SELECT id, name, cat, price, {COL_DISH_DESC}, gradient, image, created_at FROM dishes WHERE 1=1"
        params = []

        if cat and cat != "all":
            sql    += " AND cat = ?"
            params.append(cat)
        if search:
            sql    += " AND name LIKE ?"
            params.append(f"%{search}%")

        sql    += " ORDER BY created_at ASC"
        rows = fetch_all(conn, sql, params)
        # 统一返回格式（前端期望 desc 字段）
        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "name": r["name"],
                "cat": r["cat"],
                "price": r["price"],
                "desc": r.get("desc") or r.get("desc_text", ""),
                "gradient": r["gradient"],
                "image": r.get("image"),
                "created_at": str(r.get("created_at", "")),
            })
        close_db(conn)
        return make_response(out)

    elif request.method == "POST":
        data = request.get_json(silent=True) or {}
        dish_id = data.get("id") or f"dish_{uuid.uuid4().hex[:10]}"
        name    = data.get("name", "").strip()
        cat     = data.get("cat", "veg")
        price   = data.get("price", 0)
        desc    = data.get("desc", "美味新品~")
        gradient = data.get("gradient", "var(--gradient-orange)")
        image   = data.get("image") or None

        if not name:
            return make_response({"error": "菜品名称不能为空", "code": "VALIDATION_ERROR"}, 400)
        if not isinstance(price, (int, float)) or price < 0:
            return make_response({"error": "价格无效", "code": "VALIDATION_ERROR"}, 400)

        price_int = int(price)

        conn = get_db()
        try:
            is_m = _is_mysql()
            if is_m:
                execute(
                    conn,
                    f"INSERT INTO dishes (id, name, cat, price, desc_text, gradient, image) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (dish_id, name, cat, price_int, desc, gradient, image),
                )
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                execute(
                    conn,
                    "INSERT INTO dishes (id, name, cat, price, `desc`, gradient, image, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (dish_id, name, cat, price_int, desc, gradient, image, now, now),
                )
            commit(conn)
        except Exception as e:
            close_db(conn)
            return make_response({"error": str(e), "code": "DB_ERROR"}, 500)

        row = fetch_one(conn, f"SELECT id, name, cat, price, {COL_DISH_DESC}, gradient, image FROM dishes WHERE id = ?", (dish_id,))
        close_db(conn)
        result = dict(row) if row else {}
        # 统一 desc 字段
        if "desc_text" in result:
            result["desc"] = result.pop("desc_text")
        return make_response(result, 201)


@app.route("/api/dishes/<dish_id>", methods=["GET", "PUT", "DELETE"])
def dish_item(dish_id):
    conn = get_db()

    if request.method == "GET":
        row = fetch_one(conn, f"SELECT * FROM dishes WHERE id = ?", (dish_id,))
        close_db(conn)
        if not row:
            return make_response({"error": "菜品不存在", "code": "NOT_FOUND"}, 404)
        result = dict(row)
        if "desc_text" in result:
            result["desc"] = result.pop("desc_text")
        if "key_name" in result:
            result["key"] = result.pop("key_name")
        return make_response(result)

    elif request.method == "PUT":
        row = fetch_one(conn, f"SELECT * FROM dishes WHERE id = ?", (dish_id,))
        if not row:
            close_db(conn)
            return make_response({"error": "菜品不存在", "code": "NOT_FOUND"}, 404)

        data  = request.get_json(silent=True) or {}
        name    = data.get("name", row.get("name", "")).strip()
        cat     = data.get("cat", row.get("cat", "veg"))
        price   = data.get("price", row.get("price", 0))
        desc    = data.get("desc", row.get("desc", row.get("desc_text", "")))
        gradient = data.get("gradient", row.get("gradient", ""))
        image   = data.get("image", row.get("image"))

        if not name:
            close_db(conn)
            return make_response({"error": "菜品名称不能为空", "code": "VALIDATION_ERROR"}, 400)

        price_int = int(price)
        is_m = _is_mysql()

        if is_m:
            execute(
                conn,
                "UPDATE dishes SET name=?, cat=?, price=?, desc_text=?, gradient=?, image=? "
                "WHERE id=?",
                (name, cat, price_int, desc, gradient, image, dish_id),
            )
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            execute(
                conn,
                "UPDATE dishes SET name=?, cat=?, price=?, `desc`=?, gradient=?, image=?, updated_at=? "
                "WHERE id=?",
                (name, cat, price_int, desc, gradient, image, now, dish_id),
            )
        commit(conn)

        row = fetch_one(conn, f"SELECT * FROM dishes WHERE id = ?", (dish_id,))
        close_db(conn)
        result = dict(row) if row else {}
        if "desc_text" in result:
            result["desc"] = result.pop("desc_text")
        return make_response(result)

    elif request.method == "DELETE":
        row = fetch_one(conn, f"SELECT * FROM dishes WHERE id = ?", (dish_id,))
        if not row:
            close_db(conn)
            return make_response({"error": "菜品不存在", "code": "NOT_FOUND"}, 404)

        # 删除关联的图片文件（仅本地模式）
        img_val = row.get("image")
        if img_val:
            img_path = os.path.join(UPLOAD_DIR, os.path.basename(img_val))
            if os.path.isfile(img_path):
                try:
                    os.remove(img_path)
                except OSError:
                    pass

        execute(conn, "DELETE FROM dishes WHERE id = ?", (dish_id,))
        commit(conn)
        close_db(conn)
        return make_response({"deleted": True, "id": dish_id})


# ────────────────────────────────────────────────────────
#  API — 图片上传
# ────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return make_response({"error": "未选择文件", "code": "NO_FILE"}, 400)

    file = request.files["file"]
    if file.filename == "":
        return make_response({"error": "文件名为空", "code": "NO_FILE"}, 400)

    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed:
        return make_response({"error": "仅支持 JPG/PNG/GIF/WebP 格式", "code": "INVALID_TYPE"}, 400)

    ext      = os.path.splitext(file.filename)[1].lower() or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath  = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    url = f"/uploads/{filename}"
    return make_response({"url": url, "filename": filename}, 201)


# ────────────────────────────────────────────────────────
#  API — 用户状态
# ────────────────────────────────────────────────────────

@app.route("/api/user/state")
def get_user_state():
    conn = get_db()
    row = fetch_one(conn, "SELECT selected_chef, cart_json FROM user_state WHERE id = 1")
    close_db(conn)

    if not row:
        return make_response({"selectedChef": "lulu", "cart": []})

    import json
    cart = json.loads(row["cart_json"]) if row.get("cart_json") else []
    return make_response({"selectedChef": row.get("selected_chef", "lulu"), "cart": cart})


@app.route("/api/user/state", methods=["PUT"])
def update_user_state():
    data = request.get_json(silent=True) or {}
    import json

    selected_chef = data.get("selectedChef", "lulu")
    cart       = data.get("cart", [])
    cart_json  = json.dumps(cart, ensure_ascii=False)

    conn = get_db()
    execute(
        conn,
        "UPDATE user_state SET selected_chef = ?, cart_json = ? WHERE id = 1",
        (selected_chef, cart_json),
    )
    commit(conn)
    close_db(conn)

    return make_response({"selectedChef": selected_chef, "cart": cart})


# ────────────────────────────────────────────────────────
#  静态文件 & SPA 回退
# ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/<path:path>")
def serve_static(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.isfile(full_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ────────────────────────────────────────────────────────
#  启动
# ────────────────────────────────────────────────────────

if __name__ == "__main__":
    db_type = get_db_type()
    print("=" * 56)
    print("  xiaot-menu backend starting...")
    print(f"  DB mode : {db_type.upper()}")
    if db_type == "sqlite":
        print(f"  DB file : server/data.db")
    else:
        url_safe = os.environ.get('DATABASE_URL', '').split('@')[1] if '@' in os.environ.get('DATABASE_URL','') else '...'
        print(f"  TiDB URL: ...{url_safe}")
    print(f"  Uploads : server/uploads/")
    print(f"  Address: http://localhost:8080")
    print("=" * 56)
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
