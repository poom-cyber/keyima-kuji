"""
export.py — สร้างไฟล์ static จาก SQLite (kuji.db) ให้เว็บ static / pipeline เดิมใช้ต่อได้
  - site/data.json   (โครงสร้างเดิม: {rate, updated, collections:[...]})
  - site/history.json ({col_id:{pz:[[date,jp],...]}})

รันเดี่ยว ๆ:  python3 server/export.py
"""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

BASE = db.BASE

def build_data():
    with db.connect() as con:
        rate = float(db.get_meta("rate", 0.2068))
        updated = db.get_meta("updated", "")
        cols = []
        crows = con.execute("SELECT * FROM collections ORDER BY rowid").fetchall()
        prows = con.execute("SELECT * FROM prizes ORDER BY id").fetchall()
        pby = {}
        for p in prows:
            pby.setdefault(p["collection_id"], []).append({
                "pz": p["pz"], "shopee": p["shopee"], "img": p["img"] or "",
                "jp": p["jp"], "jpUrl": p["jp_url"] or "",
            })
        for c in crows:
            cols.append({
                "id": c["id"], "name": c["name"], "cover": c["cover"] or "",
                "jpkw": c["jpkw"] or "", "jpDate": c["jp_date"],
                "addedDate": c["added_date"], "createDate": c["create_date"],
                "prizes": pby.get(c["id"], []),
            })
    return {"rate": rate, "updated": updated, "collections": cols}

def build_history():
    out = {}
    with db.connect() as con:
        for r in con.execute("SELECT collection_id,pz,jp,date FROM price_history ORDER BY date"):
            out.setdefault(r["collection_id"], {}).setdefault(r["pz"], []).append([r["date"], r["jp"]])
    return out

def write_files():
    data = build_data(); hist = build_history()
    site = os.path.join(BASE, "site"); os.makedirs(site, exist_ok=True)
    json.dump(data, open(os.path.join(site, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(hist, open(os.path.join(site, "history.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return len(data["collections"]), sum(len(c["prizes"]) for c in data["collections"])

if __name__ == "__main__":
    nc, np = write_files()
    print(f"export OK -> site/data.json ({nc} cols, {np} prizes) + site/history.json")
