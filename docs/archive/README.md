# Archived Documentation

This directory contains deprecated documentation that has been superseded by the new documentation structure.

## ⚠️ Deprecated Files

### SPECIFICATION_v1.md

**Status**: Deprecated as of 2026-02-24

**Reason**: Information has been reorganized into specialized documents for better clarity and maintainability.

**Migration Guide**:

| Old (SPECIFICATION_v1.md) | New Location |
|---------------------------|--------------|
| 設計哲学 (L23-62) | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| 基本仕様 (L64-106) | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| IRデータモデル (L109-280) | [DATA_MODEL_REFERENCE.md](../DATA_MODEL_REFERENCE.md) |
| REST API仕様 (L699-1174) | [API_REFERENCE.md](../API_REFERENCE.md) |
| 標準実装パターン (L363-695) | [USAGE_PATTERNS.md](../USAGE_PATTERNS.md) |
| Distribution責任 (L283-360) | [DISTRIBUTION_GUIDE.md](../DISTRIBUTION_GUIDE.md) |

**Recommendation**: Use the new documentation structure. This file is kept for reference only.

---

## New Documentation Structure

### Tier 1: Introduction
- [README.md](../../README.md) - Project overview and quick start
- [OIDUNA_CONCEPTS.md](../OIDUNA_CONCEPTS.md) - Core concepts
- [TERMINOLOGY.md](../TERMINOLOGY.md) - Glossary

### Tier 2: Architecture
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design and ADRs
- [DATA_MODEL_REFERENCE.md](../DATA_MODEL_REFERENCE.md) - Complete IR specification
- [PERFORMANCE.md](../PERFORMANCE.md) - Performance guide

### Tier 3: API & Usage
- [API_REFERENCE.md](../API_REFERENCE.md) - HTTP API reference
- [USAGE_PATTERNS.md](../USAGE_PATTERNS.md) - Common patterns

### Tier 4: Development
- [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) - Developer guide
- [DISTRIBUTION_GUIDE.md](../DISTRIBUTION_GUIDE.md) - Building Distributions

---

**Archive Created**: 2026-02-24
**Maintained By**: Documentation team
