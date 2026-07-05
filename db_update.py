#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_update.py — ระบบเก็บประวัติราคา Kuji (เรียกหลังเขียน site/data.json ทุกรอบ)

แหล่งความจริงหลัก = history.jsonl (text, append/ปลอดภัยบนโฟลเดอร์ Windows ที่ mount)
สคริปต์นี้ idempotent: รันซ้ำวันเดิมจะ "ทับ" แถวเดิม (คีย์ = date+col_id+pz) ไม่เกิดซ้ำ

ทำให้ครบทุกรอบ:
  1) data.json: เติม collection.jpkw (คีย์เวิร์ดญี่ปุ่นสะอาด) + prize.jpUrl (ลิงก์ค้น Mercari ของรางวัลนั้น)
  2) history.jsonl: รวม snapshot วันนี้ แล้วเขียนใหม่ทั้งไฟล์แบบ de-dup (เรียงวันที่)
  3) สร้างจาก history.jsonl:
        - prices.db   (SQLite ตาราง price_history) — query ด้วย SQL ได้
        - prices.csv  (เปิดใน Excel ได้เลย)
        - prices.sql  (SQL dump เผื่อ prices.db เปิดไม่ได้: sqlite3 new.db < prices.sql)
        - site/history.json (ย่อ ให้เว็บวาดกราฟ sparkline)

ใช้: python3 db_update.py [YYYY-MM-DD]   (ไม่ใส่วันที่ = ใช้ data.json.updated)
"""
import json, sqlite3, re, sys, os, csv, shutil, tempfile, urllib.parse, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "site", "data.json")
KW   = os.path.join(BASE, "keywords.json")
JSONL= os.path.join(BASE, "history.jsonl")
CSVF = os.path.join(BASE, "prices.csv")
SITECSV = os.path.join(BASE, "site", "prices.csv")  # สำเนาให้โหลดจากเว็บ
SQLF = os.path.join(BASE, "prices.sql")
DBF  = os.path.join(BASE, "prices.db")
HIST = os.path.join(BASE, "site", "history.json")
JPDATE = os.path.join(BASE, "jpdate.json")  # state: คอลไหนอัปเดตจริงวันไหน
ADDST  = os.path.join(BASE, "addedstate.json")  # state: คอลถูกเพิ่มเข้าระบบครั้งแรกวันไหน
COLS = ["date","col_id","col_name","pz","shopee","jp","rate","jp_thb","margin"]

def clean_kw(s):
    if not s: return ""
    return re.sub(r"\s*\?ต้องเช็ก.*$", "", s).strip()

def prize_label(pz):
    s = str(pz).strip(); low = s.lower()
    if "last" in low or s in ("LO","ラストワン","ラストワン賞"): return "ラストワン"
    m = re.match(r"^([A-J])(?![A-Za-z])", s)
    return (m.group(1)+"賞") if m else ""

def mercari_url(kw, pz):
    if not kw: return ""
    q = (kw + " " + prize_label(pz)).strip()
    return "https://jp.mercari.com/search?keyword=%s&status=on_sale&sort=price&order=asc" % urllib.parse.quote(q)

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    kmap = json.load(open(KW, encoding="utf-8")).get("map", {})
    rate = data.get("rate") or 0.2043
    date = sys.argv[1] if len(sys.argv) > 1 else (data.get("updated") or datetime.date.today().isoformat())

    # 1) jpkw + jpUrl ลง data.json
    # โหลด state วันที่อัปเดตต่อคอล (เก็บลายเซ็นราคา jp ไว้เทียบว่ามีของใหม่ไหม)
    try: jpstate = json.load(open(JPDATE, encoding="utf-8"))
    except Exception: jpstate = {}
    for c in data["collections"]:
        ck = clean_kw(kmap.get(c["id"], ""))
        c["jpkw"] = ck
        for z in c["prizes"]:
            z["jpUrl"] = mercari_url(ck, z["pz"])
        # jpDate = วันที่ราคาของคอลนี้เปลี่ยนล่าสุด (ไม่มี jp เลย = null)
        if any(z.get("jp") is not None for z in c["prizes"]):
            sig = "|".join(str(z["pz"]) + ":" + str(z.get("jp")) for z in c["prizes"])
            prev = jpstate.get(c["id"])
            if (not prev) or prev.get("sig") != sig:
                jpstate[c["id"]] = {"sig": sig, "date": date}
            c["jpDate"] = jpstate[c["id"]]["date"]
        else:
            c["jpDate"] = None
    json.dump(jpstate, open(JPDATE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    # addedDate: วันที่คอลถูกเพิ่มเข้าระบบครั้งแรก (first-seen) — ใช้ sort "เพิ่มใหม่ล่าสุด"
    try: addst = json.load(open(ADDST, encoding="utf-8"))
    except Exception: addst = {}
    for c in data["collections"]:
        if c["id"] not in addst: addst[c["id"]] = date
        c["addedDate"] = addst[c["id"]]
    json.dump(addst, open(ADDST, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 2) โหลดประวัติเดิม -> dict (de-dup key)
    recs = {}
    if os.path.exists(JSONL):
        for line in open(JSONL, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            recs[(r["date"], r["col_id"], r["pz"])] = r
    # snapshot วันนี้
    for c in data["collections"]:
        for z in c["prizes"]:
            jp = z.get("jp")
            if jp is None: continue
            sh = z.get("shopee")
            r = {"date":date,"col_id":c["id"],"col_name":c["name"],"pz":z["pz"],
                 "shopee":sh,"jp":jp,"rate":rate,"jp_thb":round(jp*rate,2),
                 "margin":(round((sh-jp*rate)/sh*100,2) if sh else None)}
            recs[(date, c["id"], z["pz"])] = r
    ordered = sorted(recs.values(), key=lambda r:(r["date"], r["col_id"], str(r["pz"])))

    # เขียน history.jsonl ใหม่ทั้งไฟล์ (de-dup)
    with open(JSONL, "w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 3a) prices.csv
    with open(CSVF, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in ordered: w.writerow({k:r.get(k) for k in COLS})
    shutil.copy(CSVF, SITECSV)  # ให้โหลด prices.csv จากเว็บได้ (ข้ามเครื่อง)

    # 3b) SQLite ใน tmp (drvfs เขียน .db ตรงๆ ไม่ได้) -> prices.db + prices.sql
    workdb = os.path.join(tempfile.gettempdir(), "kuji_prices_build.db")
    if os.path.exists(workdb): os.remove(workdb)
    con = sqlite3.connect(workdb)
    con.execute("""CREATE TABLE price_history(
        date TEXT, col_id TEXT, col_name TEXT, pz TEXT,
        shopee INTEGER, jp INTEGER, rate REAL, jp_thb REAL, margin REAL,
        PRIMARY KEY(date,col_id,pz))""")
    con.executemany("INSERT OR REPLACE INTO price_history VALUES(?,?,?,?,?,?,?,?,?)",
        [tuple(r.get(k) for k in COLS) for r in ordered])
    con.commit()
    with open(SQLF, "w", encoding="utf-8") as f:
        for ln in con.iterdump(): f.write(ln + "\n")
    con.close()
    # byte-copy + fsync (โฟลเดอร์ Windows ที่ mount = drvfs ต้อง fsync ไฟล์ถึงจะอยู่ครบ)
    try:
        _b = open(workdb, "rb").read()
        with open(DBF, "wb") as _f:
            _f.write(_b); _f.flush(); os.fsync(_f.fileno())
        db_ok = True
    except Exception:
        db_ok = False

    # 4) site/history.json {col_id:{pz:[[date,jp],...]}}
    hist = {}
    for r in ordered:
        hist.setdefault(r["col_id"], {}).setdefault(str(r["pz"]), []).append([r["date"], r["jp"]])
    json.dump(hist, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, separators=(",",":"))

    ndates = len({r["date"] for r in ordered})
    print("db_update done: date=%s | total history rows=%d | distinct dates=%d" % (date, len(ordered), ndates))
    print("  data.json(jpkw+jpUrl), history.jsonl, prices.csv, prices.sql, site/history.json updated")
    print("  prices.db (SQLite binary): %s" % ("written OK" if db_ok else "skipped (drvfs) -> use prices.sql/prices.csv"))

if __name__ == "__main__":
    main()
