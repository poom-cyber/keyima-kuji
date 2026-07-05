// PATCH /api/orders/:id (admin) → เปลี่ยนสถานะออเดอร์
import { getStore } from "@netlify/blobs";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-admin-token",
  "Access-Control-Allow-Methods": "PATCH,OPTIONS",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { ...CORS, "content-type": "application/json" } });
const isAdmin = (req) => req.headers.get("x-admin-token") === (process.env.KUJI_ADMIN_TOKEN || "keyima1234");
const VALID = ["new", "confirmed", "paid", "shipped", "cancelled"];

export default async (req, context) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });
  if (req.method !== "PATCH") return json({ error: "method not allowed" }, 405);
  if (!isAdmin(req)) return json({ error: "unauthorized" }, 401);

  const id = context.params?.id;
  const { status } = await req.json();
  if (!VALID.includes(status)) return json({ error: "bad status" }, 400);

  const store = getStore("orders");
  const order = await store.get(id, { type: "json" });
  if (!order) return json({ error: "order not found" }, 404);
  order.status = status;
  await store.setJSON(id, order);
  return json({ ok: true, id, status });
};

export const config = { path: "/api/orders/:id" };
