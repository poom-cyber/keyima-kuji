"""
migrate.py — นำเข้าข้อมูลจากไฟล์เดิม (JSON) เข้า SQLite (kuji.db)
ทำให้ DB เป็น "ฐานหลัก" ใหม่ของระบบ. รันซ้ำได้ (idempotent — upsert ทับของเดิม)

  python3 server/migrate.py

อ่าน: site/data.json, keywords.json, addedstate.json, createdate.json,
       jpdate.json, history.jsonl
"""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

BASE = db.BASE

def load(path, default):
    p = os.path.join(BASE, path)
    if not os.path.exists(p):
        return default
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  ! อ่านไม่ได้", path, e); return default

def main():
    db.init_db()
    data = load("site/data.json", {"collections": [], "rate": 0.2068, "updated": ""})
    kwf = load("keywords.json", {"map": {}, "needs_check": []})
    kwmap = kwf.get("map", {})
    needs = set(kwf.get("needs_check", []))
    added = load("addedstate.json", {})
    created = load("createdate.json", {})

    with db.cursor() as con:
        # meta
        con.execute("INSERT INTO meta(key,value) VALUES('rate',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(data.get("rate", 0.2068)),))
        con.execute("INSERT INTO meta(key,value) VALUES('updated',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(data.get("updated", "")),))
        nc = np = 0
        for c in data.get("collections", []):
            cid = c["id"]
            con.execute(
                """INSERT INTO collections(id,name,cover,jpkw,jp_date,added_date,create_date)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,cover=excluded.cover,
                     jpkw=excluded.jpkw,jp_date=excluded.jp_date,
                     added_date=excluded.added_date,create_date=excluded.create_date""",
                (cid, c.get("name", ""), c.get("cover", ""), c.get("jpkw", ""),
                 c.get("jpDate"), added.get(cid) or c.get("addedDate"), created.get(cid)),
            )
            nc += 1
            for p in c.get("prizes", []):
                con.execute(
                    """INSERT INTO prizes(collection_id,pz,shopee,img,jp,jp_url)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(collection_id,pz) DO UPDATE SET shopee=excluded.shopee,
                         img=excluded.img,jp=excluded.jp,jp_url=excluded.jp_url""",
                    (cid, p["pz"], p.get("shopee"), p.get("img", ""), p.get("jp"), p.get("jpUrl", "")),
                )
                np += 1
        # keywords
        nk = 0
        for cid, kw in kwmap.items():
            con.execute(
                """INSERT INTO keywords(collection_id,keyword,needs_check) VALUES(?,?,?)
                   ON CONFLICT(collection_id) DO UPDATE SET keyword=excluded.keyword,
                     needs_check=excluded.needs_check""",
                (cid, kw, 1 if cid in needs else 0),
            )
            nk += 1
        for cid in needs:  # needs_check ที่ยังไม่มี keyword
            con.execute("INSERT OR IGNORE INTO keywords(collection_id,keyword,needs_check) VALUES(?,?,1)", (cid, ""))

    # history.jsonl -> price_history
    nh = 0
    hp = os.path.join(BASE, "history.jsonl")
    if os.path.exists(hp):
        with db.cursor() as con:
            for line in open(hp, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                con.execute(
                    """INSERT INTO price_history(collection_id,pz,jp,date) VALUES(?,?,?,?)
                       ON CONFLICT(collection_id,pz,date) DO UPDATE SET jp=excluded.jp""",
                    (r.get("col_id"), r.get("pz"), r.get("jp"), r.get("date")),
                )
                nh += 1

    print(f"migrate OK -> {db.DB_PATH}")
    print(f"  collections={nc}  prizes={np}  keywords={nk}  history_rows={nh}")

if __name__ == "__main__":
    main()
