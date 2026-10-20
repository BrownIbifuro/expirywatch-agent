import os
from datetime import date, timedelta
import pymysql

# DEMO_MODE=1 uses built-in sample data (for the public link).
# Without it, the app reads your real MySQL database.
DEMO = os.getenv("DEMO_MODE") == "1"

_SEED = [
    ("Wheat Bread", "Bakery", 12, 0), ("Fresh Milk 1L", "Dairy", 18, 1),
    ("Chicken Sausage", "Frozen", 22, 2), ("Yoghurt Cup", "Dairy", 40, 4),
    ("Butter 250g", "Dairy", 15, 6), ("Orange Juice 1L", "Beverages", 30, 8),
    ("Cough Syrup", "Pharmacy", 14, 12), ("Paracetamol 500mg", "Pharmacy", 60, 20),
    ("Tomato Paste", "Groceries", 25, 27), ("Cooking Oil 2L", "Groceries", 20, 140),
    ("Rice 5kg", "Groceries", 16, 300), ("Fish Fillet", "Frozen", 24, -397),
    ("Beans 1kg", "Groceries", 31, -382), ("Cola 50cl", "Beverages", 35, -569),
    ("Biscuits 400g", "Snacks", 28, -20), ("Sardines Tin", "Groceries", 19, -45),
    ("Corn Flakes", "Cereal", 11, -90), ("Vitamin C 1000mg", "Pharmacy", 33, -120),
]
ITEMS = []
if DEMO:
    t = date.today()
    ITEMS = [
        {"id": i + 1, "product_name": n, "category": c, "quantity": q,
         "flagged": 0, "expiry_date": t + timedelta(days=d)}
        for i, (n, c, q, d) in enumerate(_SEED)
    ]


def _conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_expiring(days):
    if DEMO:
        t, out = date.today(), []
        for it in sorted(ITEMS, key=lambda x: x["expiry_date"]):
            left = (it["expiry_date"] - t).days
            if left <= days:
                out.append({**it, "expiry_date": str(it["expiry_date"]), "days_left": left})
        return out
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, product_name, category, quantity, flagged, expiry_date,
                   DATEDIFF(expiry_date, CURDATE()) AS days_left
                   FROM inventory
                   WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                   ORDER BY expiry_date""", (days,))
            rows = cur.fetchall()
    finally:
        conn.close()
    for r in rows:
        r["expiry_date"] = str(r["expiry_date"])
    return rows


def fetch_stats():
    if DEMO:
        t = date.today()
        left = [(i["expiry_date"] - t).days for i in ITEMS]
        return {"total": len(left), "expired": sum(d < 0 for d in left),
                "soon": sum(0 <= d <= 30 for d in left)}
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS total,
                   COALESCE(SUM(expiry_date < CURDATE()), 0) AS expired,
                   COALESCE(SUM(expiry_date >= CURDATE() AND
                     expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)), 0) AS soon
                   FROM inventory""")
            row = cur.fetchone()
    finally:
        conn.close()
    return {k: int(v) for k, v in row.items()}


def flag(item_id):
    if DEMO:
        for it in ITEMS:
            if it["id"] == item_id:
                it["flagged"] = 1
        return
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE inventory SET flagged = 1 WHERE id = %s", (item_id,))
        conn.commit()
    finally:
        conn.close()
