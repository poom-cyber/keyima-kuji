#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_shopee.py — เพิ่ม/อัปเดตคอลเลคชั่นจาก CSV export ของ Shopee ลง site/data.json อย่างปลอดภัย

ใช้เมื่อ: มีคอลเลคชั่นใหม่บน Shopee หรือราคาขายเปลี่ยน
- เก็บต้นทุน jp / jpkw / jpDate / ประวัติเดิมไว้ทั้งหมด (ไม่ทับ)
- เพิ่มคอลใหม่ (jp=null -> รอบอัตโนมัติจะดึง Mercari ให้เอง, โชว์ "⚪ ยังไม่อัป")
- อัปเดตชื่อ/รูป/ราคาขาย Shopee ของคอลเดิม + เพิ่มรางวัลใหม่ถ้ามี

วิธีใช้ (วาง CSV 2 ไฟล์จาก Shopee ไว้ที่ไหนก็ได้ แล้วชี้พาธ):
   python3 merge_shopee.py "product list.csv" "photo_product_list.csv"
ไม่ใส่พาธ = หาไฟล์ *product*list*.csv / *photo*list*.csv ในโฟลเดอร์นี้อัตโนมัติ
เสร็จแล้วรัน: python3 db_update.py   (เติม jpkw/jpUrl/jpDate + ประวัติ) แล้ว deploy.bat
"""
import json, csv, sys, os, glob, io, zipfile, re
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "site", "data.json")

def read_csv(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
def _col_idx(ref):
    m = re.match(r"([A-Z]+)", ref); n = 0
    for ch in m.group(1): n = n*26 + (ord(ch)-64)
    return n-1
def read_xlsx(path):
    """อ่าน Shopee xlsx (mass-update) แบบ parse XML ตรงๆ กัน openpyxl error เรื่อง pane"""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(_NS+"si"):
            shared.append("".join(t.text or "" for t in si.iter(_NS+"t")))
    # หา sheet แรก
    sheet = next((n for n in z.namelist() if re.match(r"xl/worksheets/sheet1\.xml$", n)), None) \
            or next(n for n in z.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml"))
    root = ET.fromstring(z.read(sheet)); sd = root.find(_NS+"sheetData"); rows = []
    for row in sd.findall(_NS+"row"):
        cells = {}; maxc = -1
        for c in row.findall(_NS+"c"):
            ci = _col_idx(c.get("r")); maxc = max(maxc, ci)
            t = c.get("t"); v = c.find(_NS+"v"); isx = c.find(_NS+"is"); val = ""
            if t == "s" and v is not None: val = shared[int(v.text)]
            elif t == "inlineStr" and isx is not None: val = "".join(x.text or "" for x in isx.iter(_NS+"t"))
            elif v is not None: val = v.text
            cells[ci] = val
        rows.append([cells.get(i, "") for i in range(maxc+1)])
    return rows
def read_table(path):
    return read_xlsx(path) if path.lower().endswith(".xlsx") else read_csv(path)

def is_id(s): 
    s = (s or "").strip()
    return s.isdigit() and len(s) >= 6

def build_from_csv(sales, photo):
    """replicate ตรรกะ buildDB ของหน้าแอดมิน"""
    prod = {}
    for r in sales:
        if not r or not is_id(r[0]): continue
        cid = r[0].strip(); name = (r[1] if len(r)>1 else "").strip()
        vname = (r[3] if len(r)>3 else "").strip()
        praw = (r[6] if len(r)>6 else "")
        try: price = float("".join(ch for ch in str(praw) if (ch.isdigit() or ch=="."))) 
        except: price = None
        if cid not in prod: prod[cid] = {"id":cid,"name":name,"prizes":[],"pmap":{}}
        pz = vname.split(",")[0].strip() if "," in vname else vname.strip()
        if not pz: pz = "-"
        if pz not in prod[cid]["pmap"]:
            z = {"pz":pz,"shopee":price,"img":""}
            prod[cid]["pmap"][pz] = z; prod[cid]["prizes"].append(z)
        elif price is not None:
            o = prod[cid]["pmap"][pz]
            o["shopee"] = price if o["shopee"] is None else min(o["shopee"], price)
    ph = {}
    for r in photo:
        if not r or not is_id(r[0]): continue
        cid = r[0].strip(); cover = (r[4] if len(r)>4 else "").strip(); opt = {}
        for k in range(30):
            ni, ii = 16+2*k, 17+2*k
            nm = (r[ni] if len(r)>ni else "").strip()
            im = (r[ii] if len(r)>ii else "").strip()
            if nm: opt[nm] = im
        ph[cid] = {"cover":cover, "opt":opt}
    out = []
    for p in prod.values():
        pg = ph.get(p["id"], {"cover":"","opt":{}})
        for z in p["prizes"]:
            z["img"] = pg["opt"].get(z["pz"]) or pg["cover"] or ""
        out.append({"id":p["id"],"name":p["name"],
                    "cover":pg["cover"] or (p["prizes"][0]["img"] if p["prizes"] else ""),
                    "prizes":p["prizes"]})
    return out

def detect(paths):
    sales = photo = None
    for pth in paths:
        rows = read_table(pth)
        head = ",".join(str(x) for r in rows[:4] for x in r)  # สแกน 4 แถวแรก (xlsx มี header เป็น et_title_*)
        if "variation_price" in head or "ราคา" in head and "cover_image" not in head and "ภาพปก" not in head:
            sales = rows
        elif "cover_image" in head or "ภาพปก" in head or "item_image" in head:
            photo = rows
        else:
            sales = rows
    return sales, photo,

def update_createdate(sales):
    """เก็บ 'วันที่ create' ของสินค้าจาก CSV Shopee ลง createdate.json (id -> YYYY-MM-DD).
    ใช้สำหรับ tier ⓪ ของ AUTO_TASK (คอลใหม่ <7 วัน รีเฟรชทุกวัน). ทำแบบ defensive — ถ้าหาคอลัมน์ไม่เจอก็ข้ามเงียบๆ ไม่ทำให้ merge พัง"""
    import re as _re
    from datetime import datetime as _dt
    DATEKEYS = ("creation","create_time","create time","created","create",
                "publish","วันที่สร้าง","เวลาสร้าง","วันที่เผยแพร่","วันที่ลงขาย","วันที่")
    try:
        # หาแถว header (แถวที่มีชื่อคอลัมน์) ใน 6 แถวแรก
        hdr_idx = hdr = None
        for i, r in enumerate(sales[:6]):
            joined = ",".join(str(x).lower() for x in r)
            if "product_id" in joined or "variation_price" in joined or "ราคา" in joined:
                hdr_idx, hdr = i, r; break
        if hdr is None: return 0
        # หา index คอลัมน์วันที่ create
        col = None
        for j, name in enumerate(hdr):
            nl = str(name).lower()
            if any(k in nl for k in DATEKEYS):
                col = j; break
        if col is None: return 0
        cd = {}
        cdpath = os.path.join(BASE, "createdate.json")
        if os.path.exists(cdpath):
            try: cd = json.load(open(cdpath, encoding="utf-8"))
            except: cd = {}
        n = 0
        for r in sales[hdr_idx+1:]:
            if not r or not is_id(r[0]): continue
            cid = r[0].strip()
            raw = (r[col] if len(r) > col else "").strip()
            if not raw: continue
            iso = None
            for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%d","%Y/%m/%d %H:%M:%S",
                        "%Y/%m/%d","%d/%m/%Y %H:%M","%d/%m/%Y","%m/%d/%Y"):
                try: iso = _dt.strptime(raw[:19], fmt).strftime("%Y-%m-%d"); break
                except: pass
            if not iso:
                m = _re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
                if m: iso = "%04d-%02d-%02d" % (int(m.group(1)),int(m.group(2)),int(m.group(3)))
            if iso:
                cd[cid] = iso; n += 1
        json.dump(cd, open(cdpath,"w",encoding="utf-8"), ensure_ascii=False, indent=0)
        msg = "  + createdate.json: saved create-date for %d cols (column: %s)" % (n, hdr[col])
        print(msg)
        return n
    except Exception as e:
        print("  ! skip createdate (does not affect merge):", e); return 0

def main():
    args = [a for a in sys.argv[1:] if a.lower().endswith((".csv",".xlsx"))]
    if len(args) < 2:
        sa = (glob.glob(os.path.join(BASE,"*sales_info*.xlsx")) + glob.glob(os.path.join(BASE,"*product*list*.csv")))
        ph = (glob.glob(os.path.join(BASE,"*media_info*.xlsx")) + glob.glob(os.path.join(BASE,"*photo*list*.csv")))
        args = list(dict.fromkeys((sa[:1]+ph[:1]) or args))
    if len(args) < 2:
        print("ERROR: need 2 CSV files (product list + photo list). got:", args); sys.exit(1)
    sales, photo, = detect(args)
    if not sales or not photo:
        print("ERROR: cannot split sales/photo files - check header (need variation_price and cover_image)"); sys.exit(1)

    built = build_from_csv(sales, photo)
    data = json.load(open(DATA, encoding="utf-8"))
    existing = {c["id"]: c for c in data["collections"]}

    new_cols = 0; upd_price = 0; new_prizes = 0
    for nc in built:
        ec = existing.get(nc["id"])
        if not ec:
            for z in nc["prizes"]: z["jp"] = None
            data["collections"].append(nc); existing[nc["id"]] = nc; new_cols += 1
            continue
        if nc.get("name"): ec["name"] = nc["name"]
        if nc.get("cover"): ec["cover"] = nc["cover"]
        epz = {z["pz"]: z for z in ec["prizes"]}
        for nz in nc["prizes"]:
            if nz["pz"] in epz:
                z = epz[nz["pz"]]
                if nz["shopee"] is not None and z.get("shopee") != nz["shopee"]:
                    z["shopee"] = nz["shopee"]; upd_price += 1
                if nz["img"]: z["img"] = nz["img"]
            else:
                ec["prizes"].append({"pz":nz["pz"],"shopee":nz["shopee"],"img":nz["img"],"jp":None})
                new_prizes += 1

    json.dump(data, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    update_createdate(sales)
    print("merge_shopee done:")
    print("  + new collections added:   %d" % new_cols)
    print("  + new prizes in existing:  %d" % new_prizes)
    print("  ~ Shopee price updated:    %d" % upd_price)
    print("  total collections now:     %d" % len(data["collections"]))
    print("  (jp/jpkw/jpDate/history of existing cols = preserved)")
    print(">> next: python3 db_update.py  then double-click deploy.bat")

if __name__ == "__main__":
    main()
