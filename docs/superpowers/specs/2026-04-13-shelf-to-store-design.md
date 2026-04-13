# Shelf to Store — Design Spec
**Date:** 2026-04-13  
**Hackathon:** Anthropic + Kaszek

---

## Context

Small merchants have no e-commerce presence because the setup friction is too high. This product eliminates that friction: the merchant takes up to 3 photos of their shelves, Claude Vision extracts the products automatically, the merchant makes minor corrections, names the store, and instantly gets a public URL + QR code they can share on social media or paste in their physical store.

---

## Architecture

**Stack:** Next.js 14 (frontend) + FastAPI (backend) + SQLite (persistence)

```
Next.js (port 3000)
  /                     → Landing + photo upload
  /setup/[storeId]      → Product review & edit panel
  /store/[storeId]      → Public storefront (for customers)
  /admin/[storeId]      → Admin panel (edit store after publish)
        │
        │ HTTP
        ▼
FastAPI (port 8000)
  POST /process-images  → Launches parallel Vision agents
  POST /stores          → Creates store in SQLite
  GET  /stores/[id]     → Returns store + products
  PUT  /stores/[id]     → Updates products
        │
        │ asyncio.gather()
        ├── Claude Vision (image 1)
        ├── Claude Vision (image 2)
        └── Claude Vision (image 3)
              │
         SQLite (store.db)
```

**Store identity:** On creation, generate a short `store_id` (8-char UUID) and a long `admin_token` (full UUID). Public URL: `/store/{store_id}`. Admin URL: `/admin/{store_id}?token={admin_token}`.

---

## Core Data Flow

### Step 1 — Upload & Processing
1. Merchant uploads 1–3 photos on the landing page
2. Next.js POSTs images to `POST /process-images`
3. FastAPI runs `asyncio.gather()` — one Claude Vision call per image, in parallel
4. Each agent returns: `[{ nombre, precio, confianza }]`
5. Results are merged and deduplicated with rapidfuzz (threshold: 85%)
6. Response: unified product list

**Claude Vision prompt:**
> "Analizá esta imagen de un estante comercial. Listá cada producto visible con: nombre del producto (específico, ej: 'Coca-Cola 500ml'), precio (si está visible en etiqueta, sino null), y un nivel de confianza (high/medium/low). Devolvé JSON array con campos: nombre, precio, confianza."

### Step 2 — Edit & Publish
1. Next.js renders product cards (editable via modal) pre-filled with Claude's output
2. Low-confidence items show a yellow badge
3. Merchant corrects any errors, enters store name (+ optional WhatsApp number)
4. On "Publicar": `POST /stores` → SQLite → returns `{ store_id, admin_token }`
5. Redirect to `/store/{store_id}` — shows public URL + QR code

### Step 3 — Public Storefront
1. Customer scans QR → `/store/{store_id}`
2. Browsable product catalog with name and price
3. Add to cart (local state)
4. "Hacer pedido" opens WhatsApp with pre-filled message:
   > "Hola! Quiero pedir: [Producto A x2, Producto B x1]. Total estimado: $X"

---

## Data Model

```sql
CREATE TABLE stores (
  id          TEXT PRIMARY KEY,   -- 8-char UUID
  admin_token TEXT NOT NULL,      -- full UUID for editing
  name        TEXT NOT NULL,
  whatsapp    TEXT,               -- optional, for order button
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
  id          TEXT PRIMARY KEY,
  store_id    TEXT REFERENCES stores(id),
  name        TEXT NOT NULL,
  price       REAL,               -- null if not detected
  image_hint  TEXT,               -- description for placeholder
  position    INTEGER
);
```

---

## Project Structure

```
/
├── frontend/                    (Next.js 14)
│   ├── app/
│   │   ├── page.tsx             ← landing + upload
│   │   ├── setup/[storeId]/     ← product edit panel
│   │   ├── store/[storeId]/     ← public storefront
│   │   └── admin/[storeId]/     ← admin panel (edit after publish)
│   └── components/
│       ├── ProductCard.tsx
│       ├── EditModal.tsx
│       ├── Cart.tsx
│       └── QRDisplay.tsx
│
└── backend/                     (FastAPI)
    ├── main.py
    ├── vision.py                ← Claude Vision + dedup logic
    ├── models.py                ← Pydantic schemas
    ├── database.py              ← SQLite with sqlite3
    └── store.db
```

**Key libraries:**
- Backend: `fastapi`, `uvicorn`, `anthropic`, `rapidfuzz`, `qrcode`, `python-multipart`
- Frontend: Next.js 14, `qrcode.react`, Tailwind CSS

---

## Error Handling

| Situation | Handling |
|-----------|----------|
| Claude detects 0 products in one image | Skip that image, continue with others |
| All images return 0 products | User-friendly error: suggest better lighting |
| Price not visible in label | `price: null` → merchant fills manually |
| Low confidence detection | Yellow badge on card, merchant reviews |
| Claude API timeout | 30s timeout per image, 1 automatic retry |
| Invalid admin token | 403, without revealing store existence |

---

## Verification

1. Start both servers: `uvicorn main:app --reload` + `npm run dev`
2. Upload 2–3 shelf photos (can use supermarket photos for demo)
3. Verify products are extracted and deduplicated correctly
4. Edit one product, publish
5. Open public URL, add to cart, verify WhatsApp opens with correct message
6. Verify QR redirects to correct URL
