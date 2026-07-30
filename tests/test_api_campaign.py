"""API surface for the v1 Campaign editor (#2): image upload, the mock-campaign
seed the editor starts from, and brand-kit (palette / logo) threading through
/render-campaign. Uses FastAPI's TestClient — fully offline (no Ollama, no
browser); the campaign render is exercised in stub mode.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from layoutloom_v0.api import CampaignRequest, _resolve_brand, _safe_upload_name, app


def _png_bytes(color: str = "red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    os.chdir(tmp_path)  # endpoint writes to relative assets/uploads, output/
    return TestClient(app)


# --- filename sanitization (pure) ------------------------------------------

def test_safe_upload_name_keeps_a_clean_image_name():
    assert _safe_upload_name("photo.png") == "photo.png"


def test_safe_upload_name_lowercases_extension():
    # only the extension is normalized; the stem keeps its case
    assert _safe_upload_name("Photo.PNG") == "Photo.png"


def test_safe_upload_name_strips_directory_traversal():
    assert _safe_upload_name("../../../etc/passwd.png") == "passwd.png"


def test_safe_upload_name_sanitizes_spaces_and_punct_but_keeps_cjk():
    assert _safe_upload_name("我的圖 (1).jpg") == "我的圖_1.jpg"


def test_safe_upload_name_rejects_non_image_extension():
    with pytest.raises(Exception):
        _safe_upload_name("evil.txt")


# --- POST /upload ----------------------------------------------------

def test_upload_stores_image_and_returns_url(client: TestClient):
    r = client.post("/upload", files={"file": ("logo.png", _png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"].startswith("assets/uploads/")
    assert body["url"].startswith("/assets/uploads/")
    assert Path(body["path"]).is_file()


def test_upload_rejects_non_image(client: TestClient):
    r = client.post("/upload", files={"file": ("notes.txt", b"hi", "text/plain")})
    assert r.status_code == 422


def test_upload_dedupes_colliding_names(client: TestClient):
    a = client.post("/upload", files={"file": ("logo.png", _png_bytes("red"), "image/png")})
    b = client.post("/upload", files={"file": ("logo.png", _png_bytes("blue"), "image/png")})
    assert a.json()["path"] != b.json()["path"]
    assert Path(a.json()["path"]).is_file() and Path(b.json()["path"]).is_file()


# --- GET /campaign/mock (editor seed) --------------------------------------

def test_mock_campaign_seed_has_editable_shape(client: TestClient):
    body = client.get("/campaign/mock").json()
    assert isinstance(body["campaign"], str) and body["campaign"]
    assert len(body["products"]) == 4
    assert len(body["palette"]) == 4
    assert body["logo_path"]
    p = body["products"][0]
    for key in ("name", "product_name", "title", "subtitle", "cta", "product_image"):
        assert key in p


# --- brand-kit threading (pure) --------------------------------------------

def test_resolve_brand_uses_request_palette_and_logo():
    req = CampaignRequest(
        campaign={"campaign": "x", "products": []},
        palette=["#111111", "#222222"],
        logo_path="assets/uploads/mylogo.png",
    )
    brand = _resolve_brand(req)
    assert brand.palette == ("#111111", "#222222")
    assert brand.logo_path == Path("assets/uploads/mylogo.png")


def test_resolve_brand_falls_back_to_mock_when_unset():
    from layoutloom_v1.mockdata import MOCK_DIR, MOCK_PALETTE

    brand = _resolve_brand(CampaignRequest())
    assert brand.palette == MOCK_PALETTE
    assert brand.logo_path == MOCK_DIR / "logo.png"


# --- POST /render-campaign with a custom campaign (stub, offline) ----------

def test_render_campaign_with_uploaded_assets(client: TestClient):
    up = client.post(
        "/upload", files={"file": ("prod.png", _png_bytes(), "image/png")}
    ).json()
    campaign = {
        "campaign": "my-launch",
        "products": [
            {
                "name": "solo",
                "product_name": "Solo One",
                "title": "Solo One Launch",
                "subtitle": "Now available",
                "cta": "Buy Now",
                "product_image": up["path"],
            }
        ],
    }
    r = client.post(
        "/render-campaign",
        json={"stub": True, "campaign": campaign, "palette": ["#101820", "#f2aa4c"],
              "logo_path": up["path"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # one product x 7 GDN sizes
    assert len(body["banners"]) == 7
    assert all(b["product"] == "solo" for b in body["banners"])
