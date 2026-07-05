// POST /api/orders (public) → สร้างออเดอร์ (เช็คของหมด + แจ้งเตือน webhook)
// GET  /api/orders (admin)  → รายการออเดอร์ทั้งหมด
import { getStore } from "@netlify/blobs";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-admin-token",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { ...CORS, "content-type": "application/json" } });
const isAdmin = (req) => req.headers.get("x-admin-token") === (process.env.KUJI_ADMIN_TOKEN || "keyima1234");

async function notify(order) {
  const url = process.env.KUJI_ORDER_WEBHOOK;
  if (!url) return;
  try {
    const text =
      `🛒 ออเดอร์ใหม่ #${order.id} · ฿${Math.round(order.total).toLocaleString("en-US")}\n` +
      (order.items || []).map((i) => `▪️ ${i.name || ""} ${i.pz} ×${i.qty}`).join("\n") +
      `\n👤 ${order.customer?.name || ""} · ${order.customer?.contact || ""}`;
    await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, content: text, order }),
    });
  } catch (e) {
    console.log("webhook failed", e);
  }
}

export default async (req) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });
  const store = getStore("orders");

  if (req.method === "POST") {
    const body = await req.json();
    if (!body.items || !body.items.length) return json({ error: "empty order" }, 400);
    // เช็คของหมด
    const stock = (await getStore("shop").get("stock", { type: "json" })) || {};
    for (const it of body.items) {
      if (stock[`${it.cid}|${it.pz}`] === "out")
        return json({ error: `sold out: ${it.name || ""} ${it.pz}` }, 409);
    }
    const now = new Date();
    const id = "KYM-" + now.toISOString().slice(2, 10).replace(/-/g, "") + "-" + String(Date.now()).slice(-4);
    const order = { id, created: now.toISOString(), status: "new", items: body.items, customer: body.customer || {}, total: body.total };
    await store.setJSON(id, order);
    await notify(order);
    return json({ orderId: id, id, status: "new", total: body.total });
  }

  if (req.method === "GET") {
    if (!isAdmin(req)) return json({ error: "unauthorized" }, 401);
    const { blobs } = await store.list();
    const orders = [];
    for (const b of blobs) {
      const o = await store.get(b.key, { type: "json" });
      if (o) orders.push(o);
    }
    orders.sort((a, b) => (b.created || "").localeCompare(a.created || ""));
    return json(orders);
  }
  return json({ error: "method not allowed" }, 405);
};

export const config = { path: "/api/orders" };
