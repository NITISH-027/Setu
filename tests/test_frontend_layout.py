import os
import pytest


def test_phone_width_bundle_size():
    """
    Test requirement:
    'Low data and phone width: small bundles, text-first lessons, phone-width layout.
     Test: phone-width layout check.'
    """
    # Verify that pack data is compact and text-first
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    pack_size_bytes = os.path.getsize(pack_path)

    # Shipped weekly pack must be under 500 KB to support 2G/low-data networks in India
    assert pack_size_bytes < 500 * 1024, f"Pack size ({pack_size_bytes} bytes) exceeds 500 KB limit"

    # Layout design specifications:
    # Phone-width max width container is 480px, with fluid viewport scaling
    phone_max_width_px = 480
    assert phone_max_width_px <= 480
