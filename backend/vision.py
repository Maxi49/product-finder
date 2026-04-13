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
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
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
    CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

    def normalize(name: str) -> str:
        return name.lower().strip()

    kept: list[DetectedProduct] = []
    for candidate in products:
        is_dup = False
        for i, existing in enumerate(kept):
            score = fuzz.ratio(normalize(candidate.name), normalize(existing.name))
            if score >= 85:
                if CONFIDENCE_RANK.get(candidate.confidence, 0) > CONFIDENCE_RANK.get(existing.confidence, 0):
                    kept[i] = candidate
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)
    return kept


async def process_images(images: list[tuple[bytes, str]]) -> list[DetectedProduct]:
    tasks = [analyze_image(img_bytes, media_type) for img_bytes, media_type in images[:3]]
    results = await asyncio.gather(*tasks)
    all_products: list[DetectedProduct] = []
    for product_list in results:
        all_products.extend(product_list)
    return deduplicate_products(all_products)
