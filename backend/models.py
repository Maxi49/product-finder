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
