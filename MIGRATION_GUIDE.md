# Migration Guide: v0.x → v1.0

## Overview

Oiduna v1.0 introduces a complete architectural reorganization from 9 separate packages to a unified 4-layer structure. This guide helps you migrate existing code to the new architecture.

## Breaking Changes

### 1. Import Path Changes (CRITICAL)

All import paths have changed from `oiduna_*` to `oiduna.*`

#### Before (v0.x)
```python
from oiduna_models import Session, Track, Pattern
from oiduna_scheduler.scheduler_models import LoopSchedule, ScheduleEntry
from oiduna_session import SessionContainer, SessionCompiler
from oiduna_timeline import CuedChangeTimeline
from oiduna_loop.engine import LoopEngine
from oiduna_loop.factory import create_loop_engine
from oiduna_api.main import app
from oiduna_auth import verify_admin_password
```

#### After (v1.0)
```python
# Domain layer
from oiduna.domain.models import Session, Track, Pattern
from oiduna.domain.schedule import LoopSchedule, ScheduleEntry, SessionCompiler
from oiduna.domain.timeline import CuedChangeTimeline
from oiduna.domain.session import SessionContainer

# Infrastructure layer
from oiduna.infrastructure.execution import LoopEngine
from oiduna.infrastructure.auth import verify_admin_password

# Application layer
from oiduna.application.factory import create_loop_engine
from oiduna.application.api.main import app
```

#### Recommended: Top-level imports
```python
from oiduna import (
    Session, LoopEngine, create_loop_engine,
    SessionCompiler, CuedChangeTimeline
)
```

### 2. Package Installation

#### Before (v0.x)
```bash
pip install oiduna_api oiduna_loop oiduna_models ...  # Multiple packages
```

#### After (v1.0)
```bash
pip install oiduna  # Single unified package
```

### 3. SessionCompiler Moved

**Important:** SessionCompiler moved from `session` to `schedule` package.

#### Before
```python
from oiduna_session import SessionCompiler
```

#### After
```python
from oiduna.domain.schedule import SessionCompiler
# Or top-level:
from oiduna import SessionCompiler
```

## Complete Import Mapping Table

| Old Import (v0.x) | New Import (v1.0) | Top-level Available |
|-------------------|-------------------|---------------------|
| `from oiduna_models import Session` | `from oiduna.domain.models import Session` | ✅ `from oiduna import Session` |
| `from oiduna_models import Track` | `from oiduna.domain.models import Track` | ✅ |
| `from oiduna_models import Pattern` | `from oiduna.domain.models import Pattern` | ✅ |
| `from oiduna_models import PatternEvent` | `from oiduna.domain.models import PatternEvent` | ✅ |
| `from oiduna_models import ClientInfo` | `from oiduna.domain.models import ClientInfo` | ✅ |
| `from oiduna_models import Environment` | `from oiduna.domain.models import Environment` | ✅ |
| `from oiduna_scheduler.scheduler_models import LoopSchedule` | `from oiduna.domain.schedule import LoopSchedule` | ✅ |
| `from oiduna_scheduler.scheduler_models import ScheduleEntry` | `from oiduna.domain.schedule import ScheduleEntry` | ✅ |
| `from oiduna_session import SessionCompiler` | `from oiduna.domain.schedule import SessionCompiler` | ✅ |
| `from oiduna_session import SessionContainer` | `from oiduna.domain.session import SessionContainer` | ✅ |
| `from oiduna_timeline import CuedChangeTimeline` | `from oiduna.domain.timeline import CuedChangeTimeline` | ✅ |
| `from oiduna_timeline import CuedChange` | `from oiduna.domain.timeline import CuedChange` | ✅ |
| `from oiduna_loop.engine import LoopEngine` | `from oiduna.infrastructure.execution import LoopEngine` | ✅ |
| `from oiduna_loop.factory import create_loop_engine` | `from oiduna.application.factory import create_loop_engine` | ✅ |
| `from oiduna_api.main import app` | `from oiduna.application.api.main import app` | ✅ |
| `from oiduna_auth import verify_admin_password` | `from oiduna.infrastructure.auth import verify_admin_password` | ❌ |

## Migration Steps

### Step 1: Update Installation

```bash
# Remove old packages
pip uninstall oiduna_api oiduna_loop oiduna_models oiduna_scheduler \
    oiduna_session oiduna_timeline oiduna_auth oiduna_cli oiduna_client

# Install new unified package
pip install oiduna==1.0.0
```

### Step 2: Update Imports

Use find-and-replace in your codebase:

```bash
# Models
find . -name "*.py" -exec sed -i 's/from oiduna_models/from oiduna.domain.models/g' {} \;

# Schedule
find . -name "*.py" -exec sed -i 's/from oiduna_scheduler\.scheduler_models/from oiduna.domain.schedule/g' {} \;
find . -name "*.py" -exec sed -i 's/from oiduna_scheduler/from oiduna.domain.schedule/g' {} \;

# Session (Note: SessionCompiler is now in schedule!)
find . -name "*.py" -exec sed -i 's/from oiduna_session import SessionCompiler/from oiduna.domain.schedule import SessionCompiler/g' {} \;
find . -name "*.py" -exec sed -i 's/from oiduna_session/from oiduna.domain.session/g' {} \;

# Timeline
find . -name "*.py" -exec sed -i 's/from oiduna_timeline/from oiduna.domain.timeline/g' {} \;

# Loop Engine
find . -name "*.py" -exec sed -i 's/from oiduna_loop\.engine/from oiduna.infrastructure.execution/g' {} \;
find . -name "*.py" -exec sed -i 's/from oiduna_loop\.factory/from oiduna.application.factory/g' {} \;
find . -name "*.py" -exec sed -i 's/from oiduna_loop/from oiduna.infrastructure.execution/g' {} \;

# API
find . -name "*.py" -exec sed -i 's/from oiduna_api/from oiduna.application.api/g' {} \;

# Auth
find . -name "*.py" -exec sed -i 's/from oiduna_auth/from oiduna.infrastructure.auth/g' {} \;
```

### Step 3: Test Your Code

```bash
# Run your tests
pytest

# Check imports work
python -c "from oiduna import Session, LoopEngine, create_loop_engine"
```

## New 4-Layer Architecture

### Layer 1: Domain (`oiduna.domain`)
Business logic and domain models. No dependencies on infrastructure.

- `oiduna.domain.models` - Session, Track, Pattern, etc.
- `oiduna.domain.schedule` - LoopSchedule, SessionCompiler
- `oiduna.domain.timeline` - CuedChangeTimeline
- `oiduna.domain.session` - SessionContainer, managers

### Layer 2: Infrastructure (`oiduna.infrastructure`)
Technical implementations and external interfaces.

- `oiduna.infrastructure.execution` - LoopEngine
- `oiduna.infrastructure.routing` - Message routing
- `oiduna.infrastructure.transport` - OSC/MIDI senders
- `oiduna.infrastructure.ipc` - Inter-process communication
- `oiduna.infrastructure.auth` - Authentication

### Layer 3: Application (`oiduna.application`)
Use cases and application services.

- `oiduna.application.api` - FastAPI routes and services
- `oiduna.application.factory` - Factory functions

### Layer 4: Interface (`oiduna.interface`)
CLI and HTTP clients.

- `oiduna.interface.cli` - Command-line interface
- `oiduna.interface.client` - HTTP client library

## Benefits of New Architecture

1. **Clear Layer Separation** - Easy to understand dependencies
2. **Single Package** - Simpler installation and versioning
3. **Better IDE Support** - Better autocomplete and navigation
4. **Easier Testing** - Clear boundaries for unit/integration tests
5. **Future-Proof** - Ready for additional features and scaling

## Common Migration Issues

### Issue 1: SessionCompiler not found in session package

**Error:**
```python
ImportError: cannot import name 'SessionCompiler' from 'oiduna.domain.session'
```

**Fix:**
```python
# Change from:
from oiduna.domain.session import SessionCompiler

# To:
from oiduna.domain.schedule import SessionCompiler
```

### Issue 2: Old package names in requirements.txt

**Fix:** Update your `requirements.txt`:
```
# Remove:
oiduna_api
oiduna_loop
oiduna_models
# ... etc

# Add:
oiduna>=1.0.0
```

## Support

If you encounter migration issues:
1. Check this guide for common patterns
2. Review the new architecture documentation in `ARCHITECTURE.md`
3. File an issue at https://github.com/your-org/oiduna/issues

## Version

This migration guide applies to:
- **From:** Oiduna v0.x (multi-package architecture)
- **To:** Oiduna v1.0.0 (4-layer architecture)
