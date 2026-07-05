#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_keywords.py — อ่าน keyword ที่กรอกใน CSV กลับเข้า keywords.json
ใช้: python3 import_keywords.py keywords_to_fill.csv
แล้วรัน: python3 db_update.py  (เติม jpkw/jpUrl ให้คอลที่เพิ่งได้คีย์เวิร์ด)
รองรับคอลัมน์คีย์เวิร์ดชื่อ: 'keyword_ญี่ปุ่น_กรอกตรงนี้' หรือ 'keyword' (ตัวไหนก็ได้)
แถวที่เว้นว่าง = ข้าม (ปล่อยให้ระบบเดาเองตอนดึง)
"""
import json, csv, sys, os, glob
BASE=os.path.dirname(os.path.abspath(__file__))
KW=os.path.join(BASE,"keywords.json")
path = sys.argv[1] if len(sys.argv)>1 else (glob.glob(os.path.join(BASE,"keywords_to_fill*.csv"))+[None])[0]
if not path or not os.path.exists(path):
    print("ERROR: ไม่พบไฟล์ CSV (keywords_to_fill.csv)"); sys.exit(1)
kw=json.load(open(KW,encoding="utf-8")); kmap=kw.setdefault("map",{})
n=0
with open(path,encoding="utf-8-sig",newline="") as f:
    for row in csv.DictReader(f):
        cid=(row.get("id") or "").strip()
        val=""
        for k in row:
            if k and ("keyword" in k.lower()): val=(row[k] or "").strip()
        if cid and val:
            kmap[cid]=val; n+=1
json.dump(kw,open(KW,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("import_keywords done: เพิ่ม/อัปเดต keyword",n,"คอล ลง keywords.json")
print(">> ต่อไป: python3 db_update.py")
