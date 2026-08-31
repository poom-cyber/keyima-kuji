#!/usr/bin/env node
/*
 * mercari_fetch.cjs — ดึงต้นทุน "ซื้อได้เลยถูกสุด" จาก Mercari ญี่ปุ่น ลง site/data.json
 *
 * ใช้ Mercari search API (api.mercari.jp/v2/entities:search) พร้อม DPoP token ที่เซ็นเอง
 * ไม่ต้องใช้เบราว์เซอร์/ส่วนขยาย และไม่ติด DataDome เหมือนการดึงหน้าเว็บตรงๆ
 * ใช้ได้ทั้งบนเครื่องผู้ใช้และใน sandbox/คลาวด์ของ Claude
 *
 * ใช้:
 *   node mercari_fetch.cjs --limit 40              # เลือกคอลตามลำดับความสำคัญใน AUTO_TASK.md
 *   node mercari_fetch.cjs --ids 123,456           # เจาะจงคอล
 *   node mercari_fetch.cjs --limit 40 --dry-run    # ลองดูว่าจะได้อะไร ไม่เขียนไฟล์
 *   node mercari_fetch.cjs --limit 40 --rate 0.21  # กำหนดเรต JPY->THB เอง
 *
 * เขียน: site/data.json (prizes[].jp, updated), cursor.json (index), notfound.json
 * หลังรันเสร็จให้รัน `python3 db_update.py` ต่อ เพื่อเก็บประวัติ + เติม jpUrl
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const BASE = __dirname;
const DATA = path.join(BASE, 'site', 'data.json');
const KWF = path.join(BASE, 'keywords.json');
const CURSOR = path.join(BASE, 'cursor.json');
const CREATEDATE = path.join(BASE, 'createdate.json');

// ---------- DPoP ----------
const API = 'https://api.mercari.jp/v2/entities:search';
const b64u = (b) => Buffer.from(b).toString('base64url');
const { publicKey, privateKey } = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });
const pub = publicKey.export({ format: 'jwk' });
const JWK = { crv: 'P-256', kty: 'EC', x: pub.x, y: pub.y };

function dpop(url, method = 'POST') {
  const head = { typ: 'dpop+jwt', alg: 'ES256', jwk: JWK };
  const pay = { iat: Math.floor(Date.now() / 1000), jti: crypto.randomUUID(), htu: url, htm: method, uuid: crypto.randomUUID() };
  const signing = b64u(JSON.stringify(head)) + '.' + b64u(JSON.stringify(pay));
  const sig = crypto.sign('sha256', Buffer.from(signing), { key: privateKey, dsaEncoding: 'ieee-p1363' });
  return signing + '.' + b64u(sig);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function searchMercari(keyword, tries = 3) {
  const body = {
    userId: '', pageSize: 60, pageToken: '',
    searchSessionId: crypto.randomUUID().replace(/-/g, ''),
    indexRouting: 'INDEX_ROUTING_UNSPECIFIED', thumbnailTypes: [],
    searchCondition: {
      keyword, excludeKeyword: '', sort: 'SORT_PRICE', order: 'ORDER_ASC',
      status: ['STATUS_ON_SALE'], sizeId: [], categoryId: [], brandId: [], sellerId: [],
      priceMin: 0, priceMax: 0, itemConditionId: [], shippingPayerId: [], shippingFromArea: [],
      shippingMethod: [], colorId: [], hasCoupon: false, attributes: [], itemTypes: [],
      assignedCategoryId: [], searchConditionId: '', excludeShippingMethodIds: [],
    },
    serviceFrom: 'suruga', withItemBrand: true, withItemSize: false, withItemPromotions: true,
    withItemSizes: true, withShopname: false, useDynamicAttribute: true, withSuggestedItems: false,
    withOfferPricePromotion: true, withProductSuggest: true, withParentProducts: false,
    withProductArticles: false, withSearchConditionId: false, withAuction: true,
    defaultDatasets: ['DATASET_TYPE_MERCARI', 'DATASET_TYPE_BEYOND'],
  };
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: {
          DPoP: dpop(API), 'X-Platform': 'web', 'Content-Type': 'application/json', Accept: '*/*',
          Origin: 'https://jp.mercari.com', Referer: 'https://jp.mercari.com/',
          'Accept-Language': 'ja-JP,ja;q=0.9',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        },
        body: JSON.stringify(body),
      });
      if (res.status === 200) return (await res.json()).items || [];
      if (res.status === 429 || res.status >= 500) { await sleep(2000 * (i + 1)); continue; }
      return null; // 4xx อื่น = ถือว่าดึงไม่ได้
    } catch (e) {
      await sleep(1500 * (i + 1));
    }
  }
  return null;
}

// ---------- ตัวช่วยจับคู่รางวัล ----------
// แปลงอักษร/ตัวเลขเต็มความกว้าง -> ครึ่งความกว้าง เพื่อให้ match "Ａ賞" ได้ด้วย
function normalize(s) {
  return (s || '')
    .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0))
    .toUpperCase();
}

const LAST_ONE_RE = /ラストワン|ラスワン|LAST\s*ONE|LASTONE/;

// ชื่อรางวัลใน data.json -> คำค้นภาษาญี่ปุ่น (ตรงกับ db_update.py prize_label)
function prizeLabel(pz) {
  const s = String(pz).trim();
  const low = s.toLowerCase();
  if (low.includes('last') || low === 'lo' || ['ラストワン', 'ラストワン賞'].includes(s)) return 'ラストワン';
  const m = s.match(/^([A-J])(?![A-Za-z])/);
  return m ? m[1] + '賞' : '';
}

// ข้อความที่บอกว่าไม่ใช่ "ฟิกเกอร์รางวัลเดี่ยวพร้อมส่ง"
const BAD_RE = /まとめ|コンプ|全種|フルコンプ|一式|セット|詰め合わせ|専用|空箱|箱のみ|外箱|台紙|ジャンク|訳あり|欠品|部品|パーツ|応募|抽選|くじ券|ロット|同梱|おまとめ|台座|支柱|のみ販売|バラ売り不可|お取り置き|取り置き/;

// ชื่อขึ้นต้นด้วย "<ชื่อผู้ซื้อ>様" = จองไว้แล้ว ซื้อไม่ได้ (แต่ไม่ตัด 神様/王様 ที่อยู่กลางชื่อ)
const RESERVED_RE = /^\s*\S{1,14}様/;

// ดูว่าชื่อสินค้ามีรางวัลตัวอื่นปนหรือไม่ (= น่าจะเป็นชุดรวม)
function otherPrizeLetters(name, want) {
  const found = new Set();
  for (const m of name.matchAll(/([A-J])\s*賞/g)) found.add(m[1] + '賞');
  if (LAST_ONE_RE.test(name)) found.add('ラストワン');
  found.delete(want);
  return found.size;
}

/** เลือกราคาถูกสุดที่ "ซื้อได้เลย" และมั่นใจว่าเป็นรางวัลนั้นจริง */
function pickCheapest(items, label) {
  const out = [];
  for (const it of items) {
    if (it.auction) continue;                          // ข้ามออคชัน (ราคายังไม่นิ่ง)
    if (it.status && it.status !== 'ITEM_STATUS_ON_SALE') continue;
    const name = normalize(it.name);
    if (BAD_RE.test(name) || RESERVED_RE.test(it.name)) continue;
    const hasLabel = label === 'ラストワン' ? LAST_ONE_RE.test(name) : name.includes(label);
    if (!hasLabel) continue;                           // ไม่ระบุรางวัลชัด = ไม่เดา
    if (otherPrizeLetters(name, label) > 0) continue;  // มีหลายรางวัล = ชุดรวม
    const price = parseInt(it.price, 10);
    if (!Number.isFinite(price) || price <= 0) continue;
    out.push({ price, name: it.name, id: it.id });
  }
  out.sort((a, b) => a.price - b.price);
  return out[0] || null;
}

// ---------- เลือกคอลที่จะดึงรอบนี้ (ตาม AUTO_TASK.md ข้อ 3) ----------
function pickCollections(data, limit, cursorIdx, createdate, today) {
  const cols = data.collections;
  const hasWork = (c) => c.jpkw && c.prizes.some((p) => prizeLabel(p.pz));
  const chosen = [];
  const seen = new Set();
  const add = (c) => { if (hasWork(c) && !seen.has(c.id)) { seen.add(c.id); chosen.push(c); } };

  // ⓪ คอลใหม่ (createDate ภายใน 7 วัน) — รีเฟรชทุกรางวัลทุกวัน
  const day = 86400000;
  for (const c of cols) {
    const d = createdate[c.id];
    if (!d) continue;
    const age = (today - new Date(d + 'T00:00:00Z')) / day;
    if (age >= 0 && age <= 7) add(c);
  }
  // ① คอลที่ยังมีรางวัล jp=null — ใหม่สุดก่อน
  const pending = cols
    .filter((c) => hasWork(c) && c.prizes.some((p) => prizeLabel(p.pz) && (p.jp === null || p.jp === undefined || p.jp === '')))
    .sort((a, b) => String(b.addedDate || '').localeCompare(String(a.addedDate || '')));
  for (const c of pending) { if (chosen.length >= limit) break; add(c); }
  // ② ที่เหลือหมุนตาม cursor
  for (let i = 0; i < cols.length && chosen.length < limit; i++) {
    add(cols[(cursorIdx + i) % cols.length]);
  }
  return chosen.slice(0, limit);
}

// ---------- main ----------
function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? process.argv[i + 1] : def;
}
const FLAG = (name) => process.argv.includes('--' + name);
const VERBOSE = process.argv.includes('--verbose');

async function main() {
  const limit = parseInt(arg('limit', '40'), 10);
  const dryRun = FLAG('dry-run');
  const onlyIds = (arg('ids', '') || '').split(',').map((s) => s.trim()).filter(Boolean);
  const delayMs = parseInt(arg('delay', '350'), 10);

  const data = JSON.parse(fs.readFileSync(DATA, 'utf8'));
  const kw = JSON.parse(fs.readFileSync(KWF, 'utf8'));
  const cursor = JSON.parse(fs.readFileSync(CURSOR, 'utf8'));
  let createdate = {};
  try { createdate = JSON.parse(fs.readFileSync(CREATEDATE, 'utf8')); } catch (e) {}

  // เติม jpkw จาก keywords.json ให้คอลที่ยังไม่มี
  for (const c of data.collections) {
    if (!c.jpkw && kw.map && kw.map[c.id]) c.jpkw = String(kw.map[c.id]).replace(/\s*\?ต้องเช็ก.*$/, '').trim();
  }

  const today = new Date();
  const targets = onlyIds.length
    ? data.collections.filter((c) => onlyIds.includes(String(c.id)))
    : pickCollections(data, limit, cursor.index || 0, createdate, today);

  const rateArg = arg('rate', '');
  if (rateArg) data.rate = parseFloat(rateArg);

  let nCol = 0, nPrize = 0, nFail = 0, nReq = 0;
  const misses = [];
  const resolved = [];
  for (const c of targets) {
    let touched = false;
    for (const p of c.prizes) {
      const label = prizeLabel(p.pz);
      if (!label) continue; // ตัวเลือก Shopee ที่ไม่ใช่รางวัล (เช่น "1 กล่อง") — ปล่อยไว้
      const q = (c.jpkw + ' ' + label).trim();
      const items = await searchMercari(q);
      nReq++;
      await sleep(delayMs);
      if (items === null) { nFail++; misses.push({ id: c.id, pz: p.pz, why: 'request-failed' }); continue; }
      const best = pickCheapest(items, label);
      if (!best) { misses.push({ id: c.id, pz: p.pz, why: 'no-match', n: items.length }); continue; }
      if (p.jp !== best.price) touched = true;
      p.jp = best.price;      // เขียนทับเฉพาะที่เจอจริง
      p.jpItem = best.id;     // เก็บ id สินค้าที่เป็นที่มาของราคา
      resolved.push(c.id + '|' + p.pz);
      if (VERBOSE) console.error(`    ${p.pz}: ¥${best.price}  ${best.name.slice(0, 50)}`);
      nPrize++;
    }
    if (touched) nCol++;
    console.error(`[${nCol}/${targets.length}] ${c.id} ${String(c.name).slice(0, 40)}`);
  }

  const iso = new Date().toISOString().slice(0, 10);
  data.updated = iso;

  if (dryRun) {
    console.log(JSON.stringify({ dryRun: true, cols: targets.length, prizes: nPrize, failed: nFail, requests: nReq, misses: misses.slice(0, 30) }, null, 1));
    return;
  }

  fs.writeFileSync(DATA, JSON.stringify(data, null, 1), 'utf8');
  if (!onlyIds.length) {
    cursor.index = ((cursor.index || 0) + targets.length) % data.collections.length;
    fs.writeFileSync(CURSOR, JSON.stringify(cursor, null, 1), 'utf8');
  }
  // notfound.json = แผนที่ "<id>|<pz>": 1 ที่ site/index.html ใช้ขึ้นป้าย "ไม่เจอของขาย"
  //   คงรูปแบบเดิม: เติมรายการที่ค้นแล้วไม่เจอรอบนี้ และลบรายการที่รอบนี้เจอราคาแล้ว
  const NFF = path.join(BASE, 'site', 'notfound.json');
  let nf = {};
  try { nf = JSON.parse(fs.readFileSync(NFF, 'utf8')); } catch (e) {}
  for (const k of resolved) delete nf[k];
  for (const m of misses) { if (m.why === 'no-match') nf[m.id + '|' + m.pz] = 1; }
  fs.writeFileSync(NFF, JSON.stringify(nf, null, 1), 'utf8');
  // บันทึกรายละเอียดรอบนี้ไว้ debug (ไม่อยู่ในโฟลเดอร์ site)
  fs.writeFileSync(path.join(BASE, 'fetch_log.json'), JSON.stringify({ date: iso, cols: targets.length, prizesUpdated: nPrize, requests: nReq, failed: nFail, misses }, null, 1), 'utf8');
  console.log(JSON.stringify({ date: iso, cols: targets.length, colsChanged: nCol, prizesUpdated: nPrize, requests: nReq, failed: nFail, notMatched: misses.length }, null, 1));
}

main().catch((e) => { console.error(e); process.exit(1); });
