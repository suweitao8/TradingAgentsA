import io
import json
import logging
from fastapi.testclient import TestClient

from app.main import app


def test_config_summary_accessible():
    """单用户本地部署模式，无需认证即可访问配置摘要"""
    client = TestClient(app)
    resp = client.get("/api/system/config/summary")
    assert resp.status_code == 200


def test_config_summary_masks_sensitive_fields():
    client = TestClient(app)

    resp = client.get("/api/system/config/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert "settings" in data
    s = data["settings"]

    # Sensitive keys should exist and be masked as '***' (even if original is empty)
    for key in [
        "MONGODB_PASSWORD",
        "REDIS_PASSWORD",
        "STOCK_DATA_API_KEY",
    ]:
        assert key in s
        assert s[key] == "***"

    # Derived URIs should be present and credentials masked if any
    assert "MONGO_URI" in s
    assert "REDIS_URL" in s
    if any(x in s["MONGO_URI"] for x in ["@", ":***@"]):
        assert ":***@" in s["MONGO_URI"]
    if ":" in s["REDIS_URL"]:
        # If password was present, it must be masked
        assert "redis://:" in s["REDIS_URL"]
        # When password exists, it should be masked to *** before @
        # This assertion won't fail if no password exists (no '@' in URL)
        if "@" in s["REDIS_URL"]:
            assert "redis://:***@" in s["REDIS_URL"]

    # A few non-sensitive keys should be present for sanity
    for key in ["DEBUG", "HOST", "PORT", "MONGODB_HOST", "REDIS_HOST"]:
        assert key in s
