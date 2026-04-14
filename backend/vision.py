import asyncio
import json
import base64
import logging
from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError, APITimeoutError
from rapidfuzz import fuzz
from models import DetectedProduct

logger = logging.getLogger(__name__)

client = AsyncAnthropic()

VISION_PROMPT = """Analizá esta imagen de un estante comercial.
Listá cada producto visible con:
- nombre: nombre específico del producto (ej: 'Coca-Cola 500ml', 'Arroz Lucchetti 1kg')
- precio: precio numérico si está visible en etiqueta, sino null
- confianza: 'high' si estás seguro, 'medium' si es razonable, 'low' si es una suposición

Respondé ÚNICAMENTE con un JSON array. Ejemplo:
[{"nombre": "Coca-Cola 500ml", "precio": 150, "confianza": "high"}]

Si no hay productos visibles, respondé: []"""


class VisionError(Exception):
    """Raised when image analysis fails. Contains a user-facing reason."""
    def __init__(self, reason: str, retryable: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable


async def analyze_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[DetectedProduct]:
    """Analyze a single image. Raises VisionError on failure instead of silently returning []."""
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
    except (asyncio.TimeoutError, APITimeoutError):
        raise VisionError("La imagen tardó demasiado en procesarse (timeout 30s)", retryable=True)
    except APIStatusError as e:
        if e.status_code == 401:
            raise VisionError("API key inválida o sin permisos", retryable=False)
        if e.status_code == 429:
            raise VisionError("Límite de requests alcanzado, intentá de nuevo en unos segundos", retryable=True)
        if e.status_code >= 500:
            raise VisionError(f"Error en el servicio de Vision (HTTP {e.status_code})", retryable=True)
        raise VisionError(f"Error al analizar imagen (HTTP {e.status_code})", retryable=False)
    except APIConnectionError:
        raise VisionError("No se pudo conectar al servicio de Vision", retryable=True)

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1:
        logger.warning("Vision response contained no JSON array: %r", raw[:200])
        return []

    try:
        data = json.loads(raw[start:end])
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Vision JSON response: %s | raw=%r", e, raw[:200])
        raise VisionError("Respuesta de Vision no era JSON válido", retryable=False)

    return [
        DetectedProduct(
            name=item.get("nombre", ""),
            price=item.get("precio"),
            confidence=item.get("confianza", "medium"),
        )
        for item in data
        if item.get("nombre")
    ]


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


async def process_images(
    images: list[tuple[bytes, str]],
) -> tuple[list[DetectedProduct], list[str]]:
    """Process up to 3 images in parallel.

    Returns:
        (products, warnings) — products after dedup, warnings for any images that failed.
        If ALL images fail, raises VisionError with the first error's reason.
    """
    tasks = [analyze_image(img_bytes, media_type) for img_bytes, media_type in images[:3]]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_products: list[DetectedProduct] = []
    warnings: list[str] = []

    for idx, result in enumerate(raw_results, start=1):
        if isinstance(result, VisionError):
            logger.error("Image %d failed: %s (retryable=%s)", idx, result.reason, result.retryable)
            warnings.append(f"Imagen {idx}: {result.reason}")
        elif isinstance(result, Exception):
            logger.exception("Unexpected error processing image %d", idx)
            warnings.append(f"Imagen {idx}: error inesperado al procesar")
        else:
            all_products.extend(result)

    if not all_products and warnings:
        # Every single image failed — propagate as a hard error so the endpoint
        # returns a proper 4xx/5xx instead of an empty list that looks like success.
        raise VisionError(warnings[0], retryable=False)

    return deduplicate_products(all_products), warnings
