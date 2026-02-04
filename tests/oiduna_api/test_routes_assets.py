"""Tests for /assets/* endpoints

Tests verify asset management functionality:
- Sample upload and listing
- SynthDef upload and listing
- Storage limit enforcement
"""

import io
import pytest
from fastapi.testclient import TestClient


def test_upload_sample_success(client: TestClient, tmp_path, monkeypatch):
    """Test uploading a valid sample"""
    # Mock the assets directory
    from oiduna_api import config
    monkeypatch.setattr(config.settings, "assets_dir", tmp_path)

    # Create a mock WAV file
    wav_content = b"RIFF" + b"\x00" * 100  # Minimal WAV header
    files = {"file": ("kick.wav", io.BytesIO(wav_content), "audio/wav")}
    data = {"category": "kicks", "tags": "808,electronic"}

    response = client.post("/assets/samples", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ok"
    assert result["sample"]["name"] == "kick.wav"
    assert result["sample"]["category"] == "kicks"
    assert "808" in result["sample"]["tags"]


def test_upload_sample_invalid_extension(client: TestClient):
    """Test uploading file with invalid extension"""
    files = {"file": ("kick.mp4", io.BytesIO(b"fake content"), "video/mp4")}
    data = {"category": "kicks"}

    response = client.post("/assets/samples", files=files, data=data)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_sample_too_large(client: TestClient, monkeypatch):
    """Test uploading file exceeding size limit"""
    from oiduna_api import config
    monkeypatch.setattr(config.settings, "max_sample_size_mb", 1)

    # Create 2MB file
    large_content = b"x" * (2 * 1024 * 1024)
    files = {"file": ("large.wav", io.BytesIO(large_content), "audio/wav")}
    data = {"category": "kicks"}

    response = client.post("/assets/samples", files=files, data=data)

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_list_samples_empty(client: TestClient, tmp_path, monkeypatch):
    """Test listing samples when none exist"""
    from oiduna_api import config
    monkeypatch.setattr(config.settings, "assets_dir", tmp_path)

    response = client.get("/assets/samples")

    assert response.status_code == 200
    data = response.json()
    assert data["categories"] == {}


def test_upload_synthdef_success(client: TestClient, tmp_path, monkeypatch):
    """Test uploading a valid SynthDef"""
    from oiduna_api import config
    monkeypatch.setattr(config.settings, "assets_dir", tmp_path)

    synthdef_content = b'SynthDef(\\test, { |out=0| Out.ar(out, SinOsc.ar(440)) }).add;'
    files = {"file": ("test.scd", io.BytesIO(synthdef_content), "text/plain")}

    response = client.post("/assets/synthdefs", files=files)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ok"
    assert result["synthdef"]["name"] == "test.scd"


def test_upload_synthdef_invalid_extension(client: TestClient):
    """Test uploading file with invalid extension"""
    files = {"file": ("test.txt", io.BytesIO(b"fake content"), "text/plain")}

    response = client.post("/assets/synthdefs", files=files)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_get_assets_info(client: TestClient, tmp_path, monkeypatch):
    """Test getting asset storage info"""
    from oiduna_api import config
    monkeypatch.setattr(config.settings, "assets_dir", tmp_path)

    response = client.get("/assets/info")

    assert response.status_code == 200
    data = response.json()
    assert "storage" in data
    assert "samples" in data
    assert "synthdefs" in data
    assert "paths" in data
