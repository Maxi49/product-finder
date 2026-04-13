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
