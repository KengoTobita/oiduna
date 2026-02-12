"""Dashboard route tests"""

import pytest
from fastapi.testclient import TestClient


def test_dashboard_returns_html(client: TestClient):
    """ダッシュボードがHTMLを返す"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Oiduna Dashboard" in response.text


def test_static_css_accessible(client: TestClient):
    """CSSファイルにアクセスできる"""
    response = client.get("/static/css/dashboard.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_static_js_accessible(client: TestClient):
    """JSファイルにアクセスできる"""
    response = client.get("/static/js/dashboard.js")
    assert response.status_code == 200
