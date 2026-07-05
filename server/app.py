"""
app.py — Kuji Pricer REST API (FastAPI)

รัน dev:   uvicorn server.app:app --reload --port 8000   (จากโฟลเดอร์ PriceUpdate)
หรือ:      python3 -m uvicorn app:app --port 8000        (จากในโฟลเดอร์ server/)

เปิดเว็บแอดมิน: http://localhost:8000/      (เสิร์ฟไฟล์ web/index.html)
เอกสาร API อัตโนมัติ: http://localhost:8000/docs
"""
import os, sys, json, time, datetime, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import db, export

BASE = db.BASE
WEB = os.path.join(BASE, "web")

# ---------- shop config (env) ----------
ADMIN_TOKEN = os.environ.get("KUJI_ADMIN_TOKEN", "keyima1234")   # 👈 ตั้ง env จริงตอน deploy
ORDER_WEBHOOK = os.environ.get("KUJI_ORDER_WEBHOOK", "")          # URL รับแจ้งเตือนออเดอร์ (Discord/Telegram/Make/Google Apps Script ฯลฯ)
VALID_STATUS = ("new", "confirmed", "paid", "shipped", "cancelled")

def require_admin(token: Optional[str]):
    if token != ADMIN_TOKEN:
        raise HTTPException(401, "unauthorized")

def notify_order(oid, items, cust, total):
    if not ORDER_WEBHOOK:
        return
    try:
        text = ("🛒 ออเดอร์ใหม่ #%s · ฿%s\n" % (oid, format(round(total), ","))
                + "\n".join("▪️ %s %s ×%s" % (i.get("name", ""), i.get("pz", ""), i.get("qty", 1)) for i in items)
                + "\n👤 %s · %s" % (cust.get("name", ""), cust.get("contact", "")))
        payload = json.dumps({"orderId": oid, "items": items, "customer": cust,
                              "total": total, "text": text, "content": text}, ensure_ascii=False).encode()
        req = urllib.request.Request(ORDER_WEBHOOK, data=payload, headers={"content-type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print("order webhook failed:", e)

app = FastAPI(title="Kuji Pricer API", version="1.0",
              description="API ครอบระบบราคา Ichiban Kuji (Shopee × Mercari) — ฐานข้อมูล SQLite")
app.add_middleware(
    CORSMiddleware, allow_origins=os.environ.get("KUJI_CORS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

db.init_db()

# ---------- helpers ----------
def rate() -> float:
    return float(db.get_meta("rate", 0.2068))

def margin(shopee, jp, r):
    if not shopee or jp is None:
        return None
    return round((shopee - jp * r) / shopee * 100, 1)

def col_dict(con, c, r):
    prizes = []
    for p in con.execute("SELECT * FROM prizes WHERE collection_id=? ORDER BY id", (c["id"],)):
        prizes.append({
            "pz": p["pz"], "shopee": p["shopee"], "img": p["img"] or "",
            "jp": p["jp"], "jpUrl": p["jp_url"] or "",
            "costThb": round(p["jp"] * r) if p["jp"] is not None else None,
            "margin": margin(p["shopee"], p["jp"], r),
        })
    return {
        "id": c["id"], "name": c["name"], "cover": c["cover"] or "",
        "jpkw": c["jpkw"] or "", "jpDate": c["jp_date"],
        "addedDate": c["added_date"], "createDate": c["create_date"],
        "prizes": prizes,
    }

# ---------- models ----------
class KeywordIn(BaseModel):
    keyword: str
    needs_check: Optional[bool] = None

class KeywordImport(BaseModel):
    map: Dict[str, str]

# ---------- meta ----------
@app.get("/healthz")
def healthz():
    with db.connect() as con:
        n = con.execute("SELECT COUNT(*) c FROM collections").fetchone()["c"]
    return {"ok": True, "collections": n, "db": db.DB_PATH}

@app.get("/api/meta")
def meta():
    with db.connect() as con:
        cols = con.execute("SELECT COUNT(*) c FROM collections").fetchone()["c"]
        prizes = con.execute("SELECT COUNT(*) c FROM prizes").fetchone()["c"]
        filled = con.execute("SELECT COUNT(*) c FROM prizes WHERE jp IS NOT NULL").fetchone()["c"]
    return {"rate": rate(), "updated": db.get_meta("updated", ""),
            "collections": cols, "prizes": prizes, "prizes_with_jp": filled}

# ---------- collections ----------
@app.get("/api/collections")
def collections(q: Optional[str] = None, has_null: Optional[bool] = None, limit: int = 1000):
    r = rate()
    with db.connect() as con:
        rows = con.execute("SELECT * FROM collections ORDER BY rowid").fetchall()
        out = []
        for c in rows:
            if q and q.lower() not in (c["name"] or "").lower():
                continue
            d = col_dict(con, c, r)
            if has_null is not None:
                anynull = any(p["jp"] is None for p in d["prizes"])
                if has_null and not anynull:
                    continue
                if not has_null and anynull:
                    continue
            out.append(d)
            if len(out) >= limit:
                break
    return {"rate": r, "count": len(out), "collections": out}

@app.get("/api/collections/{cid}")
def collection(cid: str):
    with db.connect() as con:
        c = con.execute("SELECT * FROM collections WHERE id=?", (cid,)).fetchone()
        if not c:
            raise HTTPException(404, "ไม่พบคอลเลคชั่นนี้")
        return col_dict(con, c, rate())

# ---------- margins ----------
@app.get("/api/margins")
def margins(threshold: float = 55.0):
    r = rate(); out = []
    with db.connect() as con:
        rows = con.execute(
            "SELECT p.*, c.name FROM prizes p JOIN collections c ON c.id=p.collection_id "
            "WHERE p.jp IS NOT NULL AND p.shopee IS NOT NULL"
        ).fetchall()
        for p in rows:
            m = margin(p["shopee"], p["jp"], r)
            if m is not None and m < threshold:
                out.append({"id": p["collection_id"], "name": p["name"], "pz": p["pz"],
                            "jp": p["jp"], "shopee": p["shopee"],
                            "costThb": round(p["jp"] * r), "margin": m})
    out.sort(key=lambda x: x["margin"])
    return {"threshold": threshold, "rate": r, "count": len(out), "rows": out}

# ---------- keywords ----------
@app.get("/api/keywords")
def get_keywords():
    with db.connect() as con:
        rows = con.execute("SELECT * FROM keywords").fetchall()
    return {"map": {r["collection_id"]: r["keyword"] for r in rows},
            "needs_check": [r["collection_id"] for r in rows if r["needs_check"]]}

@app.put("/api/keywords/{cid}")
def put_keyword(cid: str, body: KeywordIn):
    with db.cursor() as con:
        nc = 0 if body.needs_check is False else (1 if body.needs_check else 0)
        con.execute(
            "INSERT INTO keywords(collection_id,keyword,needs_check) VALUES(?,?,?) "
            "ON CONFLICT(collection_id) DO UPDATE SET keyword=excluded.keyword, needs_check=excluded.needs_check",
            (cid, body.keyword.strip(), nc),
        )
        # sync ลง collections.jpkw ด้วย (ไว้ใช้ปุ่ม 'ก๊อปคำขอราคา')
        con.execute("UPDATE collections SET jpkw=? WHERE id=?", (body.keyword.strip(), cid))
    return {"ok": True, "id": cid, "keyword": body.keyword.strip()}

@app.post("/api/keywords/import")
def import_keywords(body: KeywordImport):
    added = updated = 0
    with db.cursor() as con:
        for cid, kw in body.map.items():
            kw = (kw or "").strip()
            if not kw:
                continue
            ex = con.execute("SELECT keyword FROM keywords WHERE collection_id=?", (cid,)).fetchone()
            if ex is None:
                added += 1
            elif ex["keyword"] != kw:
                updated += 1
            con.execute(
                "INSERT INTO keywords(collection_id,keyword,needs_check) VALUES(?,?,0) "
                "ON CONFLICT(collection_id) DO UPDATE SET keyword=excluded.keyword, needs_check=0",
                (cid, kw),
            )
            con.execute("UPDATE collections SET jpkw=? WHERE id=?", (kw, cid))
    return {"ok": True, "added": added, "updated": updated}

# ---------- history ----------
@app.get("/api/history/{cid}")
def history(cid: str):
    out = {}
    with db.connect() as con:
        for r in con.execute("SELECT pz,jp,date FROM price_history WHERE collection_id=? ORDER BY date", (cid,)):
            out.setdefault(r["pz"], []).append([r["date"], r["jp"]])
    return {"id": cid, "series": out}

# ---------- export ----------
@app.post("/api/export")
def do_export():
    try:
        nc, np = export.write_files()
    except Exception as e:
        raise HTTPException(500, f"export ล้มเหลว: {e}")
    return {"ok": True, "collections": nc, "prizes": np}

# ---------- shop: stock ----------
class StockIn(BaseModel):
    cid: str
    pz: str
    status: str   # 'out' หรือ 'in'

@app.get("/api/stock")
def get_stock():
    """คืนเฉพาะรางวัลที่ SOLD OUT: {'<cid>|<pz>': 'out'}"""
    with db.connect() as con:
        return {f"{r['collection_id']}|{r['pz']}": "out"
                for r in con.execute("SELECT collection_id, pz FROM stock WHERE status='out'")}

@app.patch("/api/stock")
def set_stock(body: StockIn, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    with db.cursor() as con:
        if body.status == "out":
            con.execute("INSERT INTO stock(collection_id,pz,status) VALUES(?,?,'out') "
                        "ON CONFLICT(collection_id,pz) DO UPDATE SET status='out'", (body.cid, body.pz))
        else:
            con.execute("DELETE FROM stock WHERE collection_id=? AND pz=?", (body.cid, body.pz))
    return {"ok": True, "cid": body.cid, "pz": body.pz, "status": body.status}

# ---------- shop: orders ----------
class OrderItem(BaseModel):
    cid: str
    pz: str
    qty: int
    price: float
    name: Optional[str] = ""

class Customer(BaseModel):
    name: str
    contact: str
    address: Optional[str] = ""
    note: Optional[str] = ""

class OrderIn(BaseModel):
    items: List[OrderItem]
    customer: Customer
    total: float

class StatusIn(BaseModel):
    status: str

@app.post("/api/orders")
def create_order(body: OrderIn):
    if not body.items:
        raise HTTPException(400, "empty order")
    with db.connect() as con:
        out = {f"{r['collection_id']}|{r['pz']}"
               for r in con.execute("SELECT collection_id, pz FROM stock WHERE status='out'")}
    for it in body.items:
        if f"{it.cid}|{it.pz}" in out:
            raise HTTPException(409, f"sold out: {it.name} {it.pz}")
    oid = "KYM-" + datetime.datetime.now().strftime("%y%m%d") + "-" + str(int(time.time()))[-4:]
    created = datetime.datetime.now().isoformat(timespec="seconds")
    items = [it.model_dump() for it in body.items]
    cust = body.customer.model_dump()
    with db.cursor() as con:
        con.execute("INSERT INTO orders(id,created,status,customer,items,total) VALUES(?,?,?,?,?,?)",
                    (oid, created, "new", json.dumps(cust, ensure_ascii=False),
                     json.dumps(items, ensure_ascii=False), body.total))
    notify_order(oid, items, cust, body.total)
    return {"orderId": oid, "id": oid, "status": "new", "total": body.total}

@app.get("/api/orders")
def list_orders(status: Optional[str] = None, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    q, args = "SELECT * FROM orders", ()
    if status:
        q += " WHERE status=?"; args = (status,)
    q += " ORDER BY created DESC"
    with db.connect() as con:
        return [{"id": r["id"], "created": r["created"], "status": r["status"],
                 "customer": json.loads(r["customer"] or "{}"),
                 "items": json.loads(r["items"] or "[]"), "total": r["total"]}
                for r in con.execute(q, args)]

@app.patch("/api/orders/{oid}")
def update_order(oid: str, body: StatusIn, x_admin_token: Optional[str] = Header(None)):
    require_admin(x_admin_token)
    if body.status not in VALID_STATUS:
        raise HTTPException(400, "bad status")
    with db.cursor() as con:
        cur = con.execute("UPDATE orders SET status=? WHERE id=?", (body.status, oid))
        if cur.rowcount == 0:
            raise HTTPException(404, "order not found")
    return {"ok": True, "id": oid, "status": body.status}

# ---------- frontend ----------
if os.path.isdir(WEB):
    app.mount("/web", StaticFiles(directory=WEB), name="web")

@app.get("/")
def index():
    f = os.path.join(WEB, "index.html")
    if os.path.exists(f):
        return FileResponse(f)
    return {"service": "Kuji Pricer API", "docs": "/docs"}
