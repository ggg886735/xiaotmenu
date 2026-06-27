"""Seed TiDB Cloud with initial data from test_data.js"""
import pymysql

# ── TiDB Cloud connection (from user's screenshot) ──
HOST = 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'
PORT = 4000
USER = 'YP1JDV94RDqhUhU.root'
PASSWORD = '9tBGwVWy3RWjqgqF'
DATABASE = 'xiaot_menu'

conn = pymysql.connect(
    host=HOST, port=PORT,
    user=USER, password=PASSWORD,
    database=DATABASE,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()
print(f'Connected to TiDB Cloud ({HOST}:{PORT}/{DATABASE})')

# ── Categories ──
categories_data = [
    ('all',   '所有菜品'),
    ('soup',  '汤品🥣'),
    ('meat',  '荤菜🍖'),
    ('veg',   '素菜🥬'),
]
for k, label in categories_data:
    cur.execute(
        "INSERT INTO categories (key_name, label) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE label=%s",
        (k, label, label)
    )
print(f'Categories: {cur.rowcount} rows')

# ── Chefs ──
chefs_data = [
    ('lulu',    '水豚噜噜', 'assets/images/2_68.png', '🐹', '汤品专家 🥣', '汤品超好喝~'),
    ('nailong', '奶龙',     'assets/images/2_74.png', '🐲', '荤菜大师 🍖', '肉肉超满足~'),
    ('beini',   '小恐龙贝尼','assets/images/2_80.png', '🦕', '素菜达人 🥬', '素菜超美味~'),
]
for ch in chefs_data:
    cur.execute(
        """INSERT INTO chefs (id, name, img, emoji, role, tag)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE name=%s,img=%s,emoji=%s,role=%s,tag=%s""",
        (*ch, ch[1], ch[2], ch[3], ch[4], ch[5])
    )
print(f'Chefs: {cur.rowcount} rows')

# ── Dishes ──
dishes_data = [
    ('fanqiedantang',      '番茄蛋汤',   'soup', 12,
     '酸甜可口，暖心暖胃~',       'var(--gradient-orange)'),
    ('dongguapaigutang',   '冬瓜排骨汤',  'soup', 22,
     '清淡鲜美，营养满分',         'var(--gradient-green)'),
    ('chaoniurou',         '炒牛肉',     'meat', 28,
     '鲜嫩多汁，肉香四溢~',       'var(--gradient-orange)'),
    ('chaokongxincai',     '炒空心菜',   'veg',  16,
     '清脆爽口，鲜嫩美味~',       'var(--gradient-green)'),
]
for d in dishes_data:
    cur.execute(
        """INSERT INTO dishes (id, name, cat, price, desc_text, gradient)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE name=%s,cat=%s,price=%s,desc_text=%s,gradient=%s""",
        (*d, d[1], d[2], d[3], d[4], d[5])
    )
print(f'Dishes: {cur.rowcount} rows')

conn.commit()

# ── Verify ──
for table in ['categories', 'chefs', 'dishes']:
    cur.execute(f'SELECT COUNT(*) AS cnt FROM {table}')
    print(f'  {table}: {cur.fetchone()["cnt"]} records')

cur.execute('SELECT id, name, cat, price FROM dishes ORDER BY cat')
print('\nDish list:')
for r in cur.fetchall():
    print(f"  [{r['cat']}] {r['name']} - \u00a5{r['price']}")

conn.close()
print('\n\u2705 CLOUD DATABASE READY!')
