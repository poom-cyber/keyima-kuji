"""
db.py — SQLite layer (ฐานข้อมูลหลักของระบบ Kuji Pricer)

ตารางหลัก:
  collections   — คอลเลคชั่น (id, ชื่อ, รูปปก, คีย์เวิร์ด Mercari, วันที่)
  prizes        — รางวัลในแต่ละคอล (pz, ราคาขาย Shopee, ต้นทุนเยน, ลิงก์, รูป)
  keywords      — แผนที่คีย์เวิร์ด + ธง needs_check
  price_history — ประวัติต้นทุนเยนรายวัน (สำหรับกราฟ)
  meta          — ค่ารวม (rate, updated)

DB path: env KUJI_DB ถ้าไม่ตั้ง = <repo>/data/kuji.db
"""
import os, sqlite3, contextlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # = PriceUpdate/
DB_PATH = os.environ.get("KUJI_DB", os.path.join(BASE, "data", "kuji.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    cover       TEXT,
    jpkw        TEXT,
    jp_date     TEXT,
    added_date  TEXT,
    create_date TEXT
);
CREATE TABLE IF NOT EXISTS prizes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id TEXT NOT NULL,
    pz            TEXT NOT NULL,
    shopee        REAL,
    img           TEXT,
    jp            INTEGER,
    jp_url        TEXT,
    UNIQUE(collection_id, pz),
    FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS keywords (
    collection_id TEXT PRIMARY KEY,
    keyword       TEXT,
    needs_check   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS price_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id TEXT NOT NULL,
    pz            TEXT NOT NULL,
    jp            INTEGER,
    date          TEXT NOT NULL,
    UNIQUE(collection_id, pz, date)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id        TEXT PRIMARY KEY,
    created   TEXT,
    status    TEXT DEFAULT 'new',
    customer  TEXT,   -- json {name,contact,address,note}
    items     TEXT,   -- json [{cid,pz,qty,price,name}]
    total     REAL
);
CREATE TABLE IF NOT EXISTS stock (
    collection_id TEXT,
    pz            TEXT,
    status        TEXT,   -- 'out' = SOLD OUT (ไม่มีแถว = พร้อมขาย)
    PRIMARY KEY(collection_id, pz)
);
CREATE INDEX IF NOT EXISTS idx_prizes_col ON prizes(collection_id);
CREATE INDEX IF NOT EXISTS idx_hist_col   ON price_history(collection_id);
CREATE INDEX IF NOT EXISTS idx_orders_st  ON orders(status);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
    return DB_PATH


@contextlib.contextmanager
def cursor():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def get_meta(key, default=None):
    with connect() as con:
        r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


def set_meta(key, value):
    with cursor() as con:
        con.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
