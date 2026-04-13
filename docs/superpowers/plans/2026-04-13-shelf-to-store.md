# Shelf to Store — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-friction e-commerce creator where merchants photograph their shelves, Claude Vision extracts products, and a public storefront + QR code are instantly generated.

**Architecture:** Next.js 14 frontend communicates with a FastAPI backend. FastAPI runs up to 3 Claude Vision calls in parallel (asyncio.gather), merges results, deduplicates with rapidfuzz, and persists everything in SQLite. The public storefront includes a cart that generates a WhatsApp order message.

**Tech Stack:** Next.js 14, Tailwind CSS, qrcode.react, FastAPI, Anthropic Python SDK, rapidfuzz, qrcode, sqlite3 (stdlib), python-multipart

---

## File Map

### Backend (`backend/`)
| File | Responsibility |
|------|---------------|
| `main.py` | FastAPI app, CORS, route registration |
| `database.py` | SQLite connection, schema init, helper queries |
| `models.py` | Pydantic request/response schemas |
| `vision.py` | Claude Vision call, response parsing, dedup logic |
| `routes/images.py` | `POST /process-images` endpoint |
| `routes/stores.py` | `POST /stores`, `GET /stores/{id}`, `PUT /stores/{id}` |

### Frontend (`frontend/`)
| File | Responsibility |
|------|---------------|
| `app/page.tsx` | Landing page with drag-and-drop photo upload |
| `app/setup/[storeId]/page.tsx` | Product review + edit panel |
| `app/store/[storeId]/page.tsx` | Public storefront (catalog + cart) |
| `app/admin/[storeId]/page.tsx` | Admin panel (edit products after publish) |
| `components/ProductCard.tsx` | Product card with edit button + confidence badge |
| `components/EditModal.tsx` | Modal form to edit name/price |
| `components/Cart.tsx` | Cart sidebar + WhatsApp order button |
| `components/QRDisplay.tsx` | QR code + shareable URL display |
| `lib/api.ts` | Typed fetch wrappers for backend endpoints |

---

## Chunk 1: Backend Foundation

### Task 1: Project scaffold + dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/database.py`

- [ ] **Step 1: Create backend directory and requirements**

```
backend/
  requirements.txt
```

```txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
anthropic==0.25.0
rapidfuzz==3.9.0
qrcode[pil]==7.4.2
python-multipart==0.0.9
pydantic==2.7.0
python-dotenv==1.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 3: Create `database.py`**

```python
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stores (
                id          TEXT PRIMARY KEY,
                admin_token TEXT NOT NULL,
                name        TEXT NOT NULL,
                whatsapp    TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id          TEXT PRIMARY KEY,
                store_id    TEXT NOT NULL REFERENCES stores(id),
                name        TEXT NOT NULL,
                price       REAL,
                image_hint  TEXT,
                position    INTEGER
            );
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def generate_store_id() -> str:
    return uuid.uuid4().hex[:8]

def generate_token() -> str:
    return str(uuid.uuid4())
```

- [ ] **Step 4: Create `main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes import images, stores

app = FastAPI(title="Shelf to Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router)
app.include_router(stores.router)

@app.on_event("startup")
def startup():
    init_db()
```

- [ ] **Step 5: Create routes package**

```bash
mkdir -p backend/routes
touch backend/routes/__init__.py
```

- [ ] **Step 6: Verify server starts**

```bash
cd backend && uvicorn main:app --reload
```
Expected: `Application startup complete.` on port 8000

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: backend scaffold with FastAPI + SQLite"
```

---

### Task 2: Pydantic models

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: Create `models.py`**

```python
from pydantic import BaseModel
from typing import Optional

class DetectedProduct(BaseModel):
    name: str
    price: Optional[float] = None
    confidence: str  # "high" | "medium" | "low"

class ProductInput(BaseModel):
    name: str
    price: Optional[float] = None
    image_hint: Optional[str] = None
    position: int = 0

class StoreCreate(BaseModel):
    name: str
    whatsapp: Optional[str] = None
    products: list[ProductInput]

class ProductOut(BaseModel):
    id: str
    name: str
    price: Optional[float]
    image_hint: Optional[str]
    position: int

class StoreOut(BaseModel):
    id: str
    name: str
    whatsapp: Optional[str]
    products: list[ProductOut]

class StoreCreated(BaseModel):
    store_id: str
    admin_token: str
    public_url: str
    admin_url: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/models.py
git commit -m "feat: pydantic models for stores and products"
```

---

## Chunk 2: Vision Processing

### Task 3: Claude Vision integration + dedup

**Files:**
- Create: `backend/vision.py`

- [ ] **Step 1: Write test for dedup logic**

```bash
mkdir -p backend/tests
touch backend/tests/__init__.py
```

```python
# backend/tests/test_vision.py
from vision import deduplicate_products
from models import DetectedProduct

def test_dedup_removes_identical():
    products = [
        DetectedProduct(name="Coca-Cola 500ml", price=150, confidence="high"),
        DetectedProduct(name="Coca-Cola 500ml", price=150, confidence="high"),
    ]
    result = deduplicate_products(products)
    assert len(result) == 1

def test_dedup_removes_fuzzy_match():
    products = [
        DetectedProduct(name="Coca Cola 500ml", price=150, confidence="high"),
        DetectedProduct(name="Coca-Cola 500 ml", price=150, confidence="medium"),
    ]
    result = deduplicate_products(products)
    assert len(result) == 1

def test_dedup_keeps_distinct():
    products = [
        DetectedProduct(name="Coca-Cola 500ml", price=150, confidence="high"),
        DetectedProduct(name="Sprite 500ml", price=130, confidence="high"),
    ]
    result = deduplicate_products(products)
    assert len(result) == 2

def test_dedup_prefers_high_confidence():
    products = [
        DetectedProduct(name="Coca Cola 500ml", price=None, confidence="low"),
        DetectedProduct(name="Coca-Cola 500ml", price=150, confidence="high"),
    ]
    result = deduplicate_products(products)
    assert len(result) == 1
    assert result[0].price == 150
    assert result[0].confidence == "high"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && python -m pytest tests/test_vision.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create `vision.py` with dedup + Claude Vision**

```python
import asyncio
import json
import base64
from anthropic import AsyncAnthropic
from rapidfuzz import fuzz
from models import DetectedProduct

client = AsyncAnthropic()

VISION_PROMPT = """Analizá esta imagen de un estante comercial.
Listá cada producto visible con:
- nombre: nombre específico del producto (ej: 'Coca-Cola 500ml', 'Arroz Lucchetti 1kg')
- precio: precio numérico si está visible en etiqueta, sino null
- confianza: 'high' si estás seguro, 'medium' si es razonable, 'low' si es una suposición

Respondé ÚNICAMENTE con un JSON array. Ejemplo:
[{"nombre": "Coca-Cola 500ml", "precio": 150, "confianza": "high"}]

Si no hay productos visibles, respondé: []"""

async def analyze_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[DetectedProduct]:
    """Call Claude Vision on a single image. Returns detected products."""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }],
            ),
            timeout=30.0,
        )
        raw = response.content[0].text.strip()
        # Extract JSON even if Claude adds surrounding text
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1:
            return []
        data = json.loads(raw[start:end])
        return [
            DetectedProduct(
                name=item.get("nombre", ""),
                price=item.get("precio"),
                confidence=item.get("confianza", "medium"),
            )
            for item in data
            if item.get("nombre")
        ]
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        return []


def deduplicate_products(products: list[DetectedProduct]) -> list[DetectedProduct]:
    """Remove near-duplicates using fuzzy name matching. Prefers higher confidence."""
    CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

    def normalize(name: str) -> str:
        return name.lower().strip()

    kept: list[DetectedProduct] = []
    for candidate in products:
        is_dup = False
        for i, existing in enumerate(kept):
            score = fuzz.ratio(normalize(candidate.name), normalize(existing.name))
            if score >= 85:
                # Keep the higher-confidence one
                if CONFIDENCE_RANK.get(candidate.confidence, 0) > CONFIDENCE_RANK.get(existing.confidence, 0):
                    kept[i] = candidate
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)
    return kept


async def process_images(images: list[tuple[bytes, str]]) -> list[DetectedProduct]:
    """Run Vision on up to 3 images in parallel, merge and deduplicate results."""
    tasks = [analyze_image(img_bytes, media_type) for img_bytes, media_type in images[:3]]
    results = await asyncio.gather(*tasks)
    all_products: list[DetectedProduct] = []
    for product_list in results:
        all_products.extend(product_list)
    return deduplicate_products(all_products)
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd backend && python -m pytest tests/test_vision.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/vision.py backend/tests/
git commit -m "feat: Claude Vision integration with fuzzy dedup"
```

---

### Task 4: Process images endpoint

**Files:**
- Create: `backend/routes/images.py`

- [ ] **Step 1: Write test**

```python
# backend/tests/test_routes_images.py
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, AsyncMock
from models import DetectedProduct

client = TestClient(app)

def test_process_images_returns_products():
    mock_products = [DetectedProduct(name="Coca-Cola 500ml", price=150, confidence="high")]
    with patch("routes.images.process_images", new=AsyncMock(return_value=mock_products)):
        with open("tests/fixtures/shelf.jpg", "rb") as f:
            response = client.post(
                "/process-images",
                files=[("images", ("shelf.jpg", f, "image/jpeg"))],
            )
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Coca-Cola 500ml"

def test_process_images_rejects_more_than_3():
    files = [("images", (f"img{i}.jpg", b"fake", "image/jpeg")) for i in range(4)]
    response = client.post("/process-images", files=files)
    assert response.status_code == 422
```

- [ ] **Step 2: Create fixture image for tests**

```bash
mkdir -p backend/tests/fixtures
# Create a minimal valid JPEG (1x1 pixel) for testing
python3 -c "
import struct, zlib
data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
open('backend/tests/fixtures/shelf.jpg', 'wb').write(data)
"
```

- [ ] **Step 3: Run test to confirm it fails**

```bash
cd backend && python -m pytest tests/test_routes_images.py -v
```
Expected: `ImportError` for missing route

- [ ] **Step 4: Create `routes/images.py`**

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated
from vision import process_images

router = APIRouter()

@router.post("/process-images")
async def process_images_endpoint(
    images: Annotated[list[UploadFile], File()]
):
    if len(images) > 3:
        raise HTTPException(status_code=422, detail="Maximum 3 images allowed")
    if len(images) == 0:
        raise HTTPException(status_code=422, detail="At least 1 image required")

    image_data = []
    for img in images:
        content = await img.read()
        media_type = img.content_type or "image/jpeg"
        image_data.append((content, media_type))

    products = await process_images(image_data)
    return {"products": [p.model_dump() for p in products]}
```

- [ ] **Step 5: Run tests — should pass**

```bash
cd backend && python -m pytest tests/test_routes_images.py -v
```
Expected: PASS (with mock)

- [ ] **Step 6: Commit**

```bash
git add backend/routes/images.py backend/tests/test_routes_images.py
git commit -m "feat: POST /process-images endpoint with parallel vision"
```

---

## Chunk 3: Store CRUD API

### Task 5: Store creation and retrieval

**Files:**
- Create: `backend/routes/stores.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_routes_stores.py
from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)

def setup_function():
    # Reset DB for each test
    database.DB_PATH.unlink(missing_ok=True)
    database.init_db()

def test_create_store_returns_urls():
    payload = {
        "name": "Mi Almacén",
        "whatsapp": "5491112345678",
        "products": [
            {"name": "Coca-Cola 500ml", "price": 150, "position": 0},
        ],
    }
    response = client.post("/stores", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "store_id" in data
    assert "admin_token" in data
    assert data["public_url"].endswith(data["store_id"])
    assert data["store_id"] in data["admin_url"]
    assert data["admin_token"] in data["admin_url"]

def test_get_store_returns_products():
    payload = {
        "name": "Mi Almacén",
        "products": [{"name": "Sprite 500ml", "price": 130, "position": 0}],
    }
    created = client.post("/stores", json=payload).json()
    store_id = created["store_id"]

    response = client.get(f"/stores/{store_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Mi Almacén"
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Sprite 500ml"

def test_get_nonexistent_store_returns_404():
    response = client.get("/stores/doesnotexist")
    assert response.status_code == 404

def test_update_store_requires_valid_token():
    payload = {"name": "Tienda", "products": [{"name": "Prod", "price": 100, "position": 0}]}
    created = client.post("/stores", json=payload).json()
    store_id = created["store_id"]

    update = {"name": "Tienda Actualizada", "products": []}
    response = client.put(f"/stores/{store_id}?token=wrongtoken", json=update)
    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_routes_stores.py -v
```

- [ ] **Step 3: Create `routes/stores.py`**

```python
import uuid
from fastapi import APIRouter, HTTPException
from models import StoreCreate, StoreOut, StoreCreated, ProductOut
from database import get_conn, generate_store_id, generate_token

router = APIRouter()

BASE_URL = "http://localhost:3000"

@router.post("/stores", status_code=201, response_model=StoreCreated)
def create_store(payload: StoreCreate):
    store_id = generate_store_id()
    admin_token = generate_token()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO stores (id, admin_token, name, whatsapp) VALUES (?, ?, ?, ?)",
            (store_id, admin_token, payload.name, payload.whatsapp),
        )
        for product in payload.products:
            conn.execute(
                "INSERT INTO products (id, store_id, name, price, image_hint, position) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), store_id, product.name, product.price, product.image_hint, product.position),
            )

    return StoreCreated(
        store_id=store_id,
        admin_token=admin_token,
        public_url=f"{BASE_URL}/store/{store_id}",
        admin_url=f"{BASE_URL}/admin/{store_id}?token={admin_token}",
    )

@router.get("/stores/{store_id}", response_model=StoreOut)
def get_store(store_id: str):
    with get_conn() as conn:
        store = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")
        products = conn.execute(
            "SELECT * FROM products WHERE store_id = ? ORDER BY position", (store_id,)
        ).fetchall()

    return StoreOut(
        id=store["id"],
        name=store["name"],
        whatsapp=store["whatsapp"],
        products=[
            ProductOut(id=p["id"], name=p["name"], price=p["price"],
                      image_hint=p["image_hint"], position=p["position"])
            for p in products
        ],
    )

@router.put("/stores/{store_id}", response_model=StoreOut)
def update_store(store_id: str, token: str, payload: StoreCreate):
    with get_conn() as conn:
        store = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")
        if store["admin_token"] != token:
            raise HTTPException(status_code=403, detail="Invalid token")

        conn.execute("UPDATE stores SET name = ?, whatsapp = ? WHERE id = ?",
                    (payload.name, payload.whatsapp, store_id))
        conn.execute("DELETE FROM products WHERE store_id = ?", (store_id,))
        for product in payload.products:
            conn.execute(
                "INSERT INTO products (id, store_id, name, price, image_hint, position) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), store_id, product.name, product.price, product.image_hint, product.position),
            )

    return get_store(store_id)
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/stores.py backend/tests/test_routes_stores.py
git commit -m "feat: store CRUD endpoints (POST, GET, PUT)"
```

---

## Chunk 4: Frontend Foundation

### Task 6: Next.js project setup

**Files:**
- Create: `frontend/` (Next.js app)

- [ ] **Step 1: Scaffold Next.js app**

```bash
cd /path/to/project
npx create-next-app@14 frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install qrcode.react
npm install -D @types/qrcode
```

- [ ] **Step 3: Create `lib/api.ts` — typed backend client**

```typescript
// frontend/lib/api.ts
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
```

- [ ] **Step 4: Verify dev server starts**

```bash
cd frontend && npm run dev
```
Expected: `http://localhost:3000` accessible

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js frontend scaffold with API client"
```

---

### Task 7: Landing page — photo upload

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Build landing page**

```tsx
// frontend/app/page.tsx
"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { processImages, DetectedProduct } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files)
      .filter((f) => f.type.startsWith("image/"))
      .slice(0, 3);
    setFiles((prev) => [...prev, ...dropped].slice(0, 3));
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []).slice(0, 3);
    setFiles(selected);
  };

  const handleSubmit = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const products = await processImages(files);
      // Store products in sessionStorage to pass to setup page
      sessionStorage.setItem("detected_products", JSON.stringify(products));
      router.push("/setup/new");
    } catch (err) {
      setError("No pudimos procesar las imágenes. Intentá de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-white flex flex-col items-center justify-center p-8">
      <div className="max-w-xl w-full">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Shelf to Store</h1>
        <p className="text-gray-500 mb-8 text-lg">
          Sacá fotos de tus estantes y publicá tu tienda online en minutos.
        </p>

        {/* Drop zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-indigo-300 rounded-2xl p-10 text-center cursor-pointer hover:border-indigo-500 transition-colors"
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <p className="text-gray-400 mb-2">Arrastrá hasta 3 fotos acá</p>
          <p className="text-sm text-gray-300">o hacé clic para seleccionar</p>
          <input
            id="file-input"
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
        </div>

        {/* Preview thumbnails */}
        {files.length > 0 && (
          <div className="flex gap-3 mt-4">
            {files.map((f, i) => (
              <div key={i} className="relative">
                <img
                  src={URL.createObjectURL(f)}
                  alt={f.name}
                  className="w-24 h-24 object-cover rounded-xl"
                />
                <button
                  onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                  className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center"
                >×</button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-red-500 mt-3 text-sm">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={files.length === 0 || loading}
          className="mt-6 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors"
        >
          {loading ? "Analizando fotos con IA..." : "Analizar fotos →"}
        </button>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify visually in browser**

Navigate to `http://localhost:3000`. You should see the landing with drag-and-drop zone.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: landing page with photo upload and drag-and-drop"
```

---

## Chunk 5: Product Edit Flow

### Task 8: ProductCard + EditModal components

**Files:**
- Create: `frontend/components/ProductCard.tsx`
- Create: `frontend/components/EditModal.tsx`

- [ ] **Step 1: Create `ProductCard.tsx`**

```tsx
// frontend/components/ProductCard.tsx
import { DetectedProduct } from "@/lib/api";

interface Props {
  product: DetectedProduct;
  index: number;
  onEdit: (index: number, updated: DetectedProduct) => void;
  onRemove: (index: number) => void;
}

const CONFIDENCE_BADGE: Record<string, string> = {
  high:   "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  low:    "bg-red-100 text-red-700",
};

export default function ProductCard({ product, index, onEdit, onRemove }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 shadow-sm">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{product.name}</p>
        <p className="text-sm text-gray-500">
          {product.price != null ? `$${product.price}` : "Precio no detectado"}
        </p>
      </div>
      <span className={`text-xs px-2 py-1 rounded-full font-medium ${CONFIDENCE_BADGE[product.confidence]}`}>
        {product.confidence}
      </span>
      <button
        onClick={() => onEdit(index, product)}
        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
      >
        Editar
      </button>
      <button
        onClick={() => onRemove(index)}
        className="text-red-400 hover:text-red-600 text-sm"
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create `EditModal.tsx`**

```tsx
// frontend/components/EditModal.tsx
"use client";
import { useState } from "react";
import { DetectedProduct } from "@/lib/api";

interface Props {
  product: DetectedProduct;
  onSave: (updated: DetectedProduct) => void;
  onClose: () => void;
}

export default function EditModal({ product, onSave, onClose }: Props) {
  const [name, setName] = useState(product.name);
  const [price, setPrice] = useState(product.price?.toString() ?? "");

  const handleSave = () => {
    onSave({
      ...product,
      name: name.trim(),
      price: price ? parseFloat(price) : null,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Editar producto</h2>
        <label className="block text-sm text-gray-600 mb-1">Nombre</label>
        <input
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <label className="block text-sm text-gray-600 mb-1">Precio ($)</label>
        <input
          type="number"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="Dejar vacío si no tiene precio"
        />
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-300 text-gray-600 py-2 rounded-xl hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="flex-1 bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-700 disabled:bg-gray-300"
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ProductCard.tsx frontend/components/EditModal.tsx
git commit -m "feat: ProductCard and EditModal components"
```

---

### Task 9: Setup page — review, edit, and publish

**Files:**
- Create: `frontend/app/setup/[storeId]/page.tsx`

- [ ] **Step 1: Create setup page**

```tsx
// frontend/app/setup/[storeId]/page.tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DetectedProduct, createStore } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import EditModal from "@/components/EditModal";

export default function SetupPage() {
  const router = useRouter();
  const [products, setProducts] = useState<DetectedProduct[]>([]);
  const [storeName, setStoreName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [editing, setEditing] = useState<{ index: number; product: DetectedProduct } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("detected_products");
    if (!raw) { router.push("/"); return; }
    setProducts(JSON.parse(raw));
  }, [router]);

  const handleEdit = (index: number, product: DetectedProduct) => {
    setEditing({ index, product });
  };

  const handleSaveEdit = (updated: DetectedProduct) => {
    setProducts((prev) => prev.map((p, i) => (i === editing!.index ? updated : p)));
    setEditing(null);
  };

  const handleRemove = (index: number) => {
    setProducts((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePublish = async () => {
    if (!storeName.trim() || products.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await createStore(
        storeName.trim(),
        whatsapp || null,
        products.map((p, i) => ({ name: p.name, price: p.price, position: i }))
      );
      sessionStorage.setItem("admin_token", result.admin_token);
      router.push(`/store/${result.store_id}?new=1&token=${result.admin_token}`);
    } catch {
      setError("Error al publicar. Intentá de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  if (products.length === 0) return null;

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Revisá tus productos</h1>
        <p className="text-gray-500 mb-6 text-sm">
          Claude detectó {products.length} productos. Editá lo que sea necesario.
        </p>

        <div className="space-y-3 mb-8">
          {products.map((p, i) => (
            <ProductCard key={i} product={p} index={i} onEdit={handleEdit} onRemove={handleRemove} />
          ))}
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
          <h2 className="font-semibold text-gray-900 mb-4">Datos de tu tienda</h2>
          <label className="block text-sm text-gray-600 mb-1">Nombre de la tienda *</label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            value={storeName}
            onChange={(e) => setStoreName(e.target.value)}
            placeholder="Ej: Almacén Don Juan"
          />
          <label className="block text-sm text-gray-600 mb-1">
            WhatsApp (opcional, para recibir pedidos)
          </label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            placeholder="5491112345678"
          />
          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
          <button
            onClick={handlePublish}
            disabled={!storeName.trim() || products.length === 0 || loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            {loading ? "Publicando..." : "Publicar tienda →"}
          </button>
        </div>
      </div>

      {editing && (
        <EditModal
          product={editing.product}
          onSave={handleSaveEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/setup/
git commit -m "feat: product review and publish flow"
```

---

## Chunk 6: Storefront + Cart + QR

### Task 10: QRDisplay component

**Files:**
- Create: `frontend/components/QRDisplay.tsx`

- [ ] **Step 1: Create `QRDisplay.tsx`**

```tsx
// frontend/components/QRDisplay.tsx
"use client";
import { QRCodeSVG } from "qrcode.react";

interface Props {
  url: string;
  adminUrl?: string;
}

export default function QRDisplay({ url, adminUrl }: Props) {
  const copyUrl = () => navigator.clipboard.writeText(url);

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-green-200 text-center">
      <p className="text-green-700 font-semibold mb-1">🎉 ¡Tu tienda está publicada!</p>
      <p className="text-sm text-gray-500 mb-4">Compartí este QR o el link con tus clientes</p>
      <div className="flex justify-center mb-4">
        <QRCodeSVG value={url} size={160} />
      </div>
      <p className="text-xs text-gray-400 break-all mb-3">{url}</p>
      <button
        onClick={copyUrl}
        className="text-indigo-600 text-sm hover:underline mr-4"
      >
        Copiar link
      </button>
      {adminUrl && (
        <a href={adminUrl} className="text-gray-400 text-xs hover:underline">
          Editar tienda →
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/QRDisplay.tsx
git commit -m "feat: QRDisplay component with share and copy"
```

---

### Task 11: Cart component

**Files:**
- Create: `frontend/components/Cart.tsx`

- [ ] **Step 1: Create `Cart.tsx`**

```tsx
// frontend/components/Cart.tsx
"use client";
import { ProductOut } from "@/lib/api";

interface CartItem {
  product: ProductOut;
  qty: number;
}

interface Props {
  items: CartItem[];
  whatsapp: string | null;
  onQtyChange: (productId: string, delta: number) => void;
}

export default function Cart({ items, whatsapp, onQtyChange }: Props) {
  const filled = items.filter((i) => i.qty > 0);
  const total = filled.reduce((sum, i) => sum + (i.product.price ?? 0) * i.qty, 0);

  const handleWhatsApp = () => {
    const lines = filled.map((i) => `${i.product.name} x${i.qty}`).join(", ");
    const msg = `Hola! Quiero pedir: ${lines}. Total estimado: $${total.toFixed(0)}`;
    const number = whatsapp ?? "";
    window.open(`https://wa.me/${number}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  if (filled.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-2xl shadow-xl border border-gray-200 p-4 w-72 z-40">
      <h3 className="font-semibold text-gray-800 mb-3">Tu pedido</h3>
      <div className="space-y-2 mb-4 max-h-40 overflow-y-auto">
        {filled.map((item) => (
          <div key={item.product.id} className="flex items-center justify-between text-sm">
            <span className="text-gray-700 truncate flex-1">{item.product.name}</span>
            <div className="flex items-center gap-2 ml-2">
              <button onClick={() => onQtyChange(item.product.id, -1)} className="w-6 h-6 bg-gray-100 rounded-full text-gray-600 hover:bg-gray-200">−</button>
              <span className="w-4 text-center">{item.qty}</span>
              <button onClick={() => onQtyChange(item.product.id, 1)} className="w-6 h-6 bg-gray-100 rounded-full text-gray-600 hover:bg-gray-200">+</button>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-sm font-medium mb-3">
        <span>Total estimado</span>
        <span>${total.toFixed(0)}</span>
      </div>
      <button
        onClick={handleWhatsApp}
        className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-xl transition-colors"
      >
        Pedir por WhatsApp
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/Cart.tsx
git commit -m "feat: Cart component with WhatsApp order"
```

---

### Task 12: Public storefront page

**Files:**
- Create: `frontend/app/store/[storeId]/page.tsx`

- [ ] **Step 1: Create storefront page**

```tsx
// frontend/app/store/[storeId]/page.tsx
"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getStore, StoreOut, ProductOut } from "@/lib/api";
import Cart from "@/components/Cart";
import QRDisplay from "@/components/QRDisplay";

interface CartItem { product: ProductOut; qty: number; }

export default function StorePage() {
  const { storeId } = useParams<{ storeId: string }>();
  const searchParams = useSearchParams();
  const isNew = searchParams.get("new") === "1";
  const adminToken = searchParams.get("token");

  const [store, setStore] = useState<StoreOut | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    getStore(storeId)
      .then((s) => {
        setStore(s);
        setCart(s.products.map((p) => ({ product: p, qty: 0 })));
      })
      .catch(() => setError(true));
  }, [storeId]);

  const handleQtyChange = (productId: string, delta: number) => {
    setCart((prev) =>
      prev.map((item) =>
        item.product.id === productId
          ? { ...item, qty: Math.max(0, item.qty + delta) }
          : item
      )
    );
  };

  const addToCart = (productId: string) => handleQtyChange(productId, 1);

  if (error) return <main className="min-h-screen flex items-center justify-center"><p className="text-gray-500">Tienda no encontrada.</p></main>;
  if (!store) return <main className="min-h-screen flex items-center justify-center"><p className="text-gray-400">Cargando...</p></main>;

  const publicUrl = `${window.location.origin}/store/${storeId}`;
  const adminUrl = adminToken ? `${window.location.origin}/admin/${storeId}?token=${adminToken}` : undefined;

  return (
    <main className="min-h-screen bg-gray-50 pb-32">
      <div className="bg-white border-b border-gray-200 px-6 py-5">
        <h1 className="text-2xl font-bold text-gray-900">{store.name}</h1>
        <p className="text-sm text-gray-400">{store.products.length} productos</p>
      </div>

      <div className="max-w-2xl mx-auto p-6">
        {isNew && (
          <div className="mb-6">
            <QRDisplay url={publicUrl} adminUrl={adminUrl} />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {store.products.map((product) => {
            const qty = cart.find((i) => i.product.id === product.id)?.qty ?? 0;
            return (
              <div key={product.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                <div className="h-24 bg-gray-100 rounded-lg mb-3 flex items-center justify-center text-gray-300 text-3xl">🛒</div>
                <p className="font-medium text-gray-900 text-sm mb-1 line-clamp-2">{product.name}</p>
                <p className="text-indigo-600 font-semibold mb-3">
                  {product.price != null ? `$${product.price}` : "Consultar precio"}
                </p>
                {qty === 0 ? (
                  <button
                    onClick={() => addToCart(product.id)}
                    className="w-full bg-indigo-600 text-white text-sm py-1.5 rounded-lg hover:bg-indigo-700"
                  >
                    Agregar
                  </button>
                ) : (
                  <div className="flex items-center justify-between">
                    <button onClick={() => handleQtyChange(product.id, -1)} className="w-8 h-8 bg-gray-100 rounded-full hover:bg-gray-200">−</button>
                    <span className="font-semibold">{qty}</span>
                    <button onClick={() => handleQtyChange(product.id, 1)} className="w-8 h-8 bg-indigo-100 text-indigo-700 rounded-full hover:bg-indigo-200">+</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <Cart items={cart} whatsapp={store.whatsapp} onQtyChange={handleQtyChange} />
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/store/
git commit -m "feat: public storefront with cart and QR display"
```

---

### Task 13: Admin panel

**Files:**
- Create: `frontend/app/admin/[storeId]/page.tsx`

- [ ] **Step 1: Create admin page**

```tsx
// frontend/app/admin/[storeId]/page.tsx
"use client";
import { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { getStore, updateStore, StoreOut, ProductOut } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import EditModal from "@/components/EditModal";
import { DetectedProduct } from "@/lib/api";

// Adapt ProductOut to DetectedProduct shape for reuse
const toDetected = (p: ProductOut): DetectedProduct => ({
  name: p.name, price: p.price, confidence: "high",
});

export default function AdminPage() {
  const { storeId } = useParams<{ storeId: string }>();
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();

  const [store, setStore] = useState<StoreOut | null>(null);
  const [products, setProducts] = useState<DetectedProduct[]>([]);
  const [storeName, setStoreName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [editing, setEditing] = useState<{ index: number; product: DetectedProduct } | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) { router.push("/"); return; }
    getStore(storeId).then((s) => {
      setStore(s);
      setStoreName(s.name);
      setWhatsapp(s.whatsapp ?? "");
      setProducts(s.products.map(toDetected));
    });
  }, [storeId, token, router]);

  const handleSave = async () => {
    setLoading(true);
    await updateStore(storeId, token, storeName, whatsapp || null,
      products.map((p, i) => ({ name: p.name, price: p.price, position: i }))
    );
    setLoading(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!store) return null;

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Administrar tienda</h1>
          <a href={`/store/${storeId}`} className="text-indigo-600 text-sm hover:underline">Ver tienda →</a>
        </div>

        <div className="space-y-3 mb-6">
          {products.map((p, i) => (
            <ProductCard key={i} product={p} index={i}
              onEdit={(idx, prod) => setEditing({ index: idx, product: prod })}
              onRemove={(idx) => setProducts((prev) => prev.filter((_, j) => j !== idx))} />
          ))}
        </div>

        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200 mb-4">
          <label className="block text-sm text-gray-600 mb-1">Nombre de la tienda</label>
          <input className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3"
            value={storeName} onChange={(e) => setStoreName(e.target.value)} />
          <label className="block text-sm text-gray-600 mb-1">WhatsApp</label>
          <input className="w-full border border-gray-300 rounded-lg px-3 py-2"
            value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
        </div>

        <button onClick={handleSave} disabled={loading}
          className="w-full bg-indigo-600 text-white font-semibold py-3 rounded-xl hover:bg-indigo-700 disabled:bg-gray-300">
          {saved ? "✓ Guardado" : loading ? "Guardando..." : "Guardar cambios"}
        </button>
      </div>

      {editing && (
        <EditModal product={editing.product}
          onSave={(u) => { setProducts((prev) => prev.map((p, i) => i === editing.index ? u : p)); setEditing(null); }}
          onClose={() => setEditing(null)} />
      )}
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/admin/
git commit -m "feat: admin panel for editing store after publish"
```

---

## Chunk 7: Integration & Final Verification

### Task 14: End-to-end test run

- [ ] **Step 1: Start backend**

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 4: Manual golden path**

1. Go to `http://localhost:3000`
2. Upload 2–3 shelf photos (use phone photos or supermarket images from Google)
3. Verify product list appears with names and prices
4. Edit one product (click "Editar")
5. Enter store name + WhatsApp number
6. Click "Publicar tienda"
7. Verify redirect to `/store/{id}` with QR code displayed
8. Add products to cart
9. Click "Pedir por WhatsApp" — verify message pre-populated correctly
10. Open admin URL — edit a product name — save — verify change reflected on public page

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: final integration verified"
```

---

## Environment Variables

Create `backend/.env` (not committed):
```
ANTHROPIC_API_KEY=your_key_here
```

Load in `main.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

Add `python-dotenv` to `requirements.txt`.

Create `frontend/.env.local` (not committed):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
