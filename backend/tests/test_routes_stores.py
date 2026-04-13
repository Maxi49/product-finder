import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)


def setup_function():
    database.DB_PATH.unlink(missing_ok=True)
    database.init_db()


def test_create_store_returns_urls():
    payload = {
        "name": "Mi Almacen",
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
        "name": "Mi Almacen",
        "products": [{"name": "Sprite 500ml", "price": 130, "position": 0}],
    }
    created = client.post("/stores", json=payload).json()
    store_id = created["store_id"]

    response = client.get(f"/stores/{store_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Mi Almacen"
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


def test_update_store_with_valid_token():
    payload = {"name": "Tienda", "products": [{"name": "Prod", "price": 100, "position": 0}]}
    created = client.post("/stores", json=payload).json()
    store_id = created["store_id"]
    token = created["admin_token"]

    update = {"name": "Tienda Actualizada", "products": [{"name": "Nuevo Prod", "price": 200, "position": 0}]}
    response = client.put(f"/stores/{store_id}?token={token}", json=update)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tienda Actualizada"
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Nuevo Prod"
