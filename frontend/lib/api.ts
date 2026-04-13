const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface DetectedProduct {
  name: string;
  price: number | null;
  confidence: "high" | "medium" | "low";
}

export interface ProductInput {
  name: string;
  price: number | null;
  image_hint?: string;
  position: number;
}

export interface ProductOut {
  id: string;
  name: string;
  price: number | null;
  image_hint: string | null;
  position: number;
}

export interface StoreOut {
  id: string;
  name: string;
  whatsapp: string | null;
  products: ProductOut[];
}

export interface StoreCreated {
  store_id: string;
  admin_token: string;
  public_url: string;
  admin_url: string;
}

export async function processImages(files: File[]): Promise<DetectedProduct[]> {
  const form = new FormData();
  files.forEach((f) => form.append("images", f));
  const res = await fetch(`${API_BASE}/process-images`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.products;
}

export async function createStore(
  name: string,
  whatsapp: string | null,
  products: ProductInput[]
): Promise<StoreCreated> {
  const res = await fetch(`${API_BASE}/stores`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, whatsapp, products }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getStore(storeId: string): Promise<StoreOut> {
  const res = await fetch(`${API_BASE}/stores/${storeId}`);
  if (!res.ok) throw new Error("Store not found");
  return res.json();
}

export async function updateStore(
  storeId: string,
  token: string,
  name: string,
  whatsapp: string | null,
  products: ProductInput[]
): Promise<StoreOut> {
  const res = await fetch(`${API_BASE}/stores/${storeId}?token=${token}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, whatsapp, products }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
