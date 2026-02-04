"""POST /assets/* - Asset management endpoints for custom samples and SynthDefs

This module handles:
- Uploading custom samples (.wav, .aif, .aiff, .aifc)
- Uploading SynthDefs (.scd)
- Listing and deleting assets
- Integration with SuperDirt directory structure
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from oiduna_api.config import settings

router = APIRouter()

# Allowed file extensions
SAMPLE_EXTENSIONS = {".wav", ".aif", ".aiff", ".aifc"}
SYNTHDEF_EXTENSION = ".scd"

# Metadata file
METADATA_FILE = settings.assets_dir / "metadata.json"


class SampleInfo(BaseModel):
    """Information about an uploaded sample"""
    name: str
    category: str
    path: str
    size: int
    uploaded_at: str
    tags: list[str] = Field(default_factory=list)


class SynthDefInfo(BaseModel):
    """Information about an uploaded SynthDef"""
    name: str
    path: str
    uploaded_at: str


class SamplesResponse(BaseModel):
    """Response listing all samples grouped by category"""
    categories: dict[str, list[SampleInfo]]


class UploadResponse(BaseModel):
    """Response after successful upload"""
    status: str
    sample: SampleInfo | None = None
    synthdef: SynthDefInfo | None = None


# Helper functions

def load_metadata() -> dict[str, Any]:
    """Load metadata from file"""
    if METADATA_FILE.exists():
        with open(METADATA_FILE) as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {"samples": {}, "synthdefs": {}}


def save_metadata(metadata: dict[str, Any]):
    """Save metadata to file"""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def get_sample_info(category: str, filename: str) -> SampleInfo | None:
    """Get sample info from metadata"""
    metadata = load_metadata()
    key = f"{category}/{filename}"
    sample_meta = metadata["samples"].get(key)

    if not sample_meta:
        return None

    sample_path = settings.samples_dir / category / filename
    if not sample_path.exists():
        return None

    return SampleInfo(
        name=filename,
        category=category,
        path=str(sample_path.relative_to(settings.assets_dir)),
        size=sample_path.stat().st_size,
        uploaded_at=sample_meta.get("uploaded_at", ""),
        tags=sample_meta.get("tags", [])
    )


def calculate_total_size() -> int:
    """Calculate total size of all samples"""
    total = 0
    if settings.samples_dir.exists():
        for sample_file in settings.samples_dir.rglob("*"):
            if sample_file.is_file():
                total += sample_file.stat().st_size
    return total


# Endpoints

@router.post("/samples", response_model=UploadResponse)
async def upload_sample(
    file: UploadFile = File(...),
    category: str = Form(..., description="Sample category (e.g., 'kicks', 'snares')"),
    tags: str = Form("", description="Comma-separated tags")
):
    """Upload a custom sample file

    The sample will be placed in: oiduna_data/samples/{category}/{filename}
    SuperDirt will recognize it as: sound "{category}"

    Example:
        Upload kick.wav to category "kicks"
        → Use in Oiduna: {"sound": "kicks", ...}
    """

    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SAMPLE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {SAMPLE_EXTENSIONS}"
        )

    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_sample_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max: {settings.max_sample_size_mb}MB"
        )

    # Check total size limit
    total_size_gb = calculate_total_size() / (1024 * 1024 * 1024)
    if total_size_gb > settings.max_total_samples_gb:
        raise HTTPException(
            status_code=507,
            detail=f"Storage limit exceeded ({total_size_gb:.1f}GB). Max: {settings.max_total_samples_gb}GB"
        )

    # Save file
    category_dir = settings.samples_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)

    sample_path = category_dir / file.filename
    with open(sample_path, "wb") as f:
        f.write(content)

    # Update metadata
    metadata = load_metadata()
    key = f"{category}/{file.filename}"
    metadata["samples"][key] = {
        "uploaded_at": datetime.now().isoformat(),
        "original_name": file.filename,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "size": len(content)
    }
    save_metadata(metadata)

    sample_info = SampleInfo(
        name=file.filename,
        category=category,
        path=str(sample_path.relative_to(settings.assets_dir)),
        size=len(content),
        uploaded_at=metadata["samples"][key]["uploaded_at"],
        tags=metadata["samples"][key]["tags"]
    )

    return UploadResponse(status="ok", sample=sample_info)


@router.get("/samples", response_model=SamplesResponse)
async def list_samples():
    """List all uploaded samples grouped by category"""

    categories: dict[str, list[SampleInfo]] = {}

    if not settings.samples_dir.exists():
        return SamplesResponse(categories={})

    # Scan all sample files
    for category_dir in settings.samples_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name
        samples = []

        for sample_file in category_dir.iterdir():
            if sample_file.is_file() and sample_file.suffix.lower() in SAMPLE_EXTENSIONS:
                info = get_sample_info(category, sample_file.name)
                if info:
                    samples.append(info)

        if samples:
            categories[category] = samples

    return SamplesResponse(categories=categories)


@router.delete("/samples/{category}/{filename}")
async def delete_sample(category: str, filename: str):
    """Delete a sample"""

    sample_path = settings.samples_dir / category / filename
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample not found")

    # Delete file
    sample_path.unlink()

    # Update metadata
    metadata = load_metadata()
    key = f"{category}/{filename}"
    metadata["samples"].pop(key, None)
    save_metadata(metadata)

    # Remove category directory if empty
    category_dir = settings.samples_dir / category
    if category_dir.exists() and not list(category_dir.iterdir()):
        category_dir.rmdir()

    return {"status": "ok", "deleted": f"{category}/{filename}"}


@router.post("/synthdefs", response_model=UploadResponse)
async def upload_synthdef(file: UploadFile = File(...)):
    """Upload a SynthDef (.scd file)

    The SynthDef will be placed in: oiduna_data/synthdefs/{filename}

    Note: You need to configure SuperCollider to load SynthDefs from this directory.
    See docs/distribution-guide.md for setup instructions.
    """

    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate file extension
    if not file.filename.endswith(SYNTHDEF_EXTENSION):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Must be {SYNTHDEF_EXTENSION}"
        )

    # Save file
    settings.synthdefs_dir.mkdir(parents=True, exist_ok=True)
    synthdef_path = settings.synthdefs_dir / file.filename

    content = await file.read()
    with open(synthdef_path, "wb") as f:
        f.write(content)

    # Update metadata
    metadata = load_metadata()
    metadata["synthdefs"][file.filename] = {
        "uploaded_at": datetime.now().isoformat(),
        "path": str(synthdef_path)
    }
    save_metadata(metadata)

    synthdef_info = SynthDefInfo(
        name=file.filename,
        path=str(synthdef_path.relative_to(settings.assets_dir)),
        uploaded_at=metadata["synthdefs"][file.filename]["uploaded_at"]
    )

    return UploadResponse(status="ok", synthdef=synthdef_info)


@router.get("/synthdefs", response_model=list[SynthDefInfo])
async def list_synthdefs():
    """List all uploaded SynthDefs"""

    synthdefs = []

    if not settings.synthdefs_dir.exists():
        return synthdefs

    metadata = load_metadata()

    for synthdef_file in settings.synthdefs_dir.glob(f"*{SYNTHDEF_EXTENSION}"):
        synthdef_meta = metadata["synthdefs"].get(synthdef_file.name, {})

        synthdefs.append(SynthDefInfo(
            name=synthdef_file.name,
            path=str(synthdef_file.relative_to(settings.assets_dir)),
            uploaded_at=synthdef_meta.get("uploaded_at", "")
        ))

    return synthdefs


@router.delete("/synthdefs/{filename}")
async def delete_synthdef(filename: str):
    """Delete a SynthDef"""

    if not filename.endswith(SYNTHDEF_EXTENSION):
        filename += SYNTHDEF_EXTENSION

    synthdef_path = settings.synthdefs_dir / filename
    if not synthdef_path.exists():
        raise HTTPException(status_code=404, detail="SynthDef not found")

    # Delete file
    synthdef_path.unlink()

    # Update metadata
    metadata = load_metadata()
    metadata["synthdefs"].pop(filename, None)
    save_metadata(metadata)

    return {"status": "ok", "deleted": filename}


@router.get("/info")
async def get_assets_info():
    """Get assets storage information"""

    total_size = calculate_total_size()
    total_size_mb = total_size / (1024 * 1024)

    # Count samples by category
    sample_count = 0
    categories = {}
    if settings.samples_dir.exists():
        for category_dir in settings.samples_dir.iterdir():
            if category_dir.is_dir():
                count = len(list(category_dir.glob("*")))
                if count > 0:
                    categories[category_dir.name] = count
                    sample_count += count

    # Count synthdefs
    synthdef_count = 0
    if settings.synthdefs_dir.exists():
        synthdef_count = len(list(settings.synthdefs_dir.glob(f"*{SYNTHDEF_EXTENSION}")))

    return {
        "storage": {
            "total_size_mb": round(total_size_mb, 2),
            "limit_mb": settings.max_sample_size_mb,
            "total_limit_gb": settings.max_total_samples_gb
        },
        "samples": {
            "total": sample_count,
            "categories": categories
        },
        "synthdefs": {
            "total": synthdef_count
        },
        "paths": {
            "samples": str(settings.samples_dir),
            "synthdefs": str(settings.synthdefs_dir)
        }
    }
