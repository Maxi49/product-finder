import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
