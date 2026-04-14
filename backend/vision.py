import asyncio
import json
import base64
import logging
from anthropic import AsyncAnthropic, APIError, APITimeoutError, APIConnectionError
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
    """Base exception for vision processing failures."""


class VisionTimeoutError(VisionError):
    """Claude API call timed out."""


class VisionAPIError(VisionError):
    """Claude API returned an error (auth, quota, network, etc.)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class VisionParseError(VisionError):
    """Claude responded but the output could not be parsed as valid product JSON."""

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


async def analyze_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[DetectedProduct]:
    """Analyze a single shelf image and return detected products.

    Raises:
        VisionTimeoutError: API call exceeded 30 s.
        VisionAPIError: Anthropic API returned an error.
        VisionParseError: Response could not be parsed as product JSON.
    """
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
    except asyncio.TimeoutError as exc:
        logger.warning("Vision API timeout after 30s")
        raise VisionTimeoutError("Vision API call timed out after 30 seconds") from exc
    except APITimeoutError as exc:
        logger.warning("Anthropic SDK timeout: %s", exc)
        raise VisionTimeoutError(str(exc)) from exc
    except APIConnectionError as exc:
        logger.error("Anthropic API connection error: %s", exc)
        raise VisionAPIError(f"Connection error: {exc}") from exc
    except APIError as exc:
        logger.error("Anthropic API error %s: %s", exc.status_code, exc.message)
        raise VisionAPIError(exc.message, status_code=exc.status_code) from exc

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1

    if start == -1 or end == 0:
        logger.warning("Vision response missing JSON array. Raw: %.200s", raw)
        raise VisionParseError("Response did not contain a JSON array", raw=raw)

    try:
        data = json.loads(raw[start:end])
    except json.JSONDecodeError as exc:
        logger.warning("Vision response JSON parse failed: %s. Raw: %.200s", exc, raw)
        raise VisionParseError(f"JSON decode error: {exc}", raw=raw[start:end]) from exc

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


async def process_images(images: list[tuple[bytes, str]]) -> tuple[list[DetectedProduct], list[VisionError]]:
    """Process up to 3 shelf images concurrently.

    Returns a tuple of (products, errors). Partial success is allowed:
    if 1 of 3 images fails, detected products from the remaining images
    are still returned alongside the collected errors.
    """
    tasks = [analyze_image(img_bytes, media_type) for img_bytes, media_type in images[:3]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_products: list[DetectedProduct] = []
    errors: list[VisionError] = []

    for i, result in enumerate(results):
        if isinstance(result, VisionError):
            logger.error("Image %d failed: %s", i + 1, result)
            errors.append(result)
        elif isinstance(result, BaseException):
            logger.error("Image %d unexpected error: %s", i + 1, result)
            errors.append(VisionError(str(result)))
        else:
            all_products.extend(result)

    return deduplicate_products(all_products), errors
