import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from vision import deduplicate_products, process_images, VisionError
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


# --- process_images error handling ---

def _fake_image() -> tuple[bytes, str]:
    return b"\xff\xd8\xff", "image/jpeg"


def test_process_images_partial_failure_returns_products_and_warnings():
    """One image fails, one succeeds — returns products from success with a warning."""
    good_products = [DetectedProduct(name="Sprite 500ml", price=130, confidence="high")]

    async def _analyze(image_bytes, media_type="image/jpeg"):
        if image_bytes == b"bad":
            raise VisionError("timeout", retryable=True)
        return good_products

    async def run():
        with patch("vision.analyze_image", side_effect=_analyze):
            return await process_images([(_fake_image()[0], "image/jpeg"), (b"bad", "image/jpeg")])

    products, warnings = asyncio.run(run())
    assert len(products) == 1
    assert products[0].name == "Sprite 500ml"
    assert len(warnings) == 1
    assert "timeout" in warnings[0]


def test_process_images_all_fail_raises_vision_error():
    """When every image fails, process_images raises VisionError."""
    async def _analyze(image_bytes, media_type="image/jpeg"):
        raise VisionError("API key inválida", retryable=False)

    async def run():
        with patch("vision.analyze_image", side_effect=_analyze):
            return await process_images([(_fake_image()[0], "image/jpeg")])

    try:
        asyncio.run(run())
        assert False, "Expected VisionError"
    except VisionError as e:
        assert "API key" in e.reason


def test_process_images_no_warnings_on_full_success():
    """All images succeed — warnings list is empty."""
    good = [DetectedProduct(name="Fanta 350ml", price=80, confidence="medium")]

    async def _analyze(image_bytes, media_type="image/jpeg"):
        return good

    async def run():
        with patch("vision.analyze_image", side_effect=_analyze):
            return await process_images([(_fake_image()[0], "image/jpeg")])

    products, warnings = asyncio.run(run())
    assert len(products) == 1
    assert warnings == []
