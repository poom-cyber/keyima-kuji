// GET /api/stock  (public)   → { "<cid>|<pz>": "out", ... }
// PATCH /api/stock (admin)    body { cid, pz, status:"out"|"in" }
import { getStore } from "@netlify/blobs";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-admin-token",
  "Access-Control-Allow-Methods": "GET,PATCH,OPTIONS",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { ...CORS, "content-type": "application/json" } });
const isAdmin = (req) => req.headers.get("x-admin-token") === (process.env.KUJI_ADMIN_TOKEN || "keyima1234");

export default async (req) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });
  const shop = getStore("shop");

  if (req.method === "GET") {
    const stock = (await shop.get("stock", { type: "json" })) || {};
    return json(stock);
  }
  if (req.method === "PATCH") {
    if (!isAdmin(req)) return json({ error: "unauthorized" }, 401);
    const { cid, pz, status } = await req.json();
    if (!cid || !pz) return json({ error: "cid/pz required" }, 400);
    const stock = (await shop.get("stock", { type: "json" })) || {};
    if (status === "out") stock[`${cid}|${pz}`] = "out";
    else delete stock[`${cid}|${pz}`];
    await shop.setJSON("stock", stock);
    return json({ ok: true, cid, pz, status });
  }
  return json({ error: "method not allowed" }, 405);
};

export const config = { path: "/api/stock" };
