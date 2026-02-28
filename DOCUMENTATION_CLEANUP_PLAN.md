# Documentation Cleanup Plan

**Date**: 2026-02-28

**Reason**: After ADR-0010 (SessionContainer refactoring), many documents contain outdated architecture information that could mislead developers.

---

## Critical: Delete Immediately

### ❌ GLOSSARY.md (ROOT)
**Reason**: Contains completely outdated architecture (pre-SessionContainer). Mentions non-existent SessionManager Facade pattern.

**Harmful Content**:
- No mention of SessionContainer, ClientManager, TrackManager, etc.
- References old Session/Pattern concepts that don't match current API
- `POST /playback/session` API described but SessionCompiler flow completely different now
- Last updated: 2026-02-25 (before ADR-0010 implementation)

**Action**: **DELETE** and replace with reference to:
- `docs/OIDUNA_CONCEPTS.md` (updated with SessionContainer)
- `docs/TERMINOLOGY.md` (terminology without architecture details)
- `docs/API_REFERENCE.md` (current API endpoints)

---

## Archive to docs/archive/

These files are historical records but should not be in root:

### 📦 PHASE_1_2_SUMMARY.md
**Content**: Phase 1 & 2 implementation summary (Session/Track/Pattern models, REST API)
**Last Updated**: Phase 2 completion
**Action**: Move to `docs/archive/phase-1-2-summary.md`

### 📦 PHASE_3_SUMMARY.md
**Content**: Phase 3 implementation summary (Loop Engine integration, SSE events)
**Last Updated**: Phase 3 completion
**Action**: Move to `docs/archive/phase-3-summary.md`

### 📦 ARCHITECTURE_REFACTORING_STATUS.md
**Content**: Phase 1-3 implementation status tracking
**Last Updated**: Phase 3 completion (before ADR-0008, ADR-0010)
**Action**: Move to `docs/archive/architecture-refactoring-status.md`

### 📦 REVIEW_JP.md
**Content**: Japanese project review (seems to be from earlier phases)
**Last Updated**: Unknown
**Action**: Move to `docs/archive/review-jp.md`

---

## Update in Place

### ✏️ IMPLEMENTATION_COMPLETE.md (ROOT)
**Content**: Phase 1-4 completion summary
**Status**: Needs update with ADR-0010 changes (SessionContainer refactoring)
**Action**: Add section on ADR-0010 implementation, update test counts (578 tests)

### ✏️ REFACTORING_REPORT.md (ROOT)
**Content**: Code quality and refactoring recommendations
**Status**: Some recommendations implemented (SessionManager split), needs update
**Action**: Mark completed items (SessionManager → SessionContainer), update metrics

### ✏️ COVERAGE_REPORT.md (ROOT)
**Content**: Test coverage analysis
**Status**: Needs update with new integration tests (17 new tests)
**Action**: Update coverage numbers, add integration test section

### ✏️ TESTING_AND_QUALITY_SUMMARY.md (ROOT)
**Content**: Testing strategy and quality metrics
**Status**: Needs update with SessionContainer tests
**Action**: Update test counts, add manager unit tests section

---

## Keep as-is (Recent and Accurate)

### ✅ CLAUDE.md (ROOT)
**Content**: Guide for Claude Code working on Oiduna
**Last Updated**: 2026-02-28
**Action**: Keep (up to date)

### ✅ README.md (ROOT)
**Content**: Project overview, setup instructions
**Action**: Keep (verify accuracy)

### ✅ CHANGELOG.md (ROOT)
**Content**: Version history
**Action**: Keep (add ADR-0010 entry if missing)

---

## Delete (Low Value or Redundant)

### ❌ benchmark_plan.md (ROOT)
**Content**: Extension hook performance benchmark plan
**Status**: Not implemented, speculative
**Action**: **DELETE** or move to docs/archive/benchmarking/ if needed

---

## docs/ Directory Review

### Update Required

#### docs/ARCHITECTURE.md
**Check**: Does it mention SessionManager or SessionContainer?
**Action**: Update if outdated

#### docs/DATA_MODEL_REFERENCE.md
**Check**: Session/Track/Pattern models match current implementation?
**Action**: Verify and update

#### docs/API_REFERENCE.md
**Check**: API endpoints match current routes?
**Action**: Verify all endpoints

#### docs/OIDUNA_CONCEPTS.md
**Check**: Core concepts reflect SessionContainer architecture?
**Action**: Update if needed

#### docs/TERMINOLOGY.md
**Check**: Terms match current codebase?
**Action**: Update if needed

### Potentially Outdated

#### docs/ARCHITECTURE_UNIFICATION_COMPLETE.md
**Date**: 2026-02-26 (before ADR-0010)
**Action**: Review and update or archive

#### docs/MIGRATION_GUIDE_SCHEDULED_MESSAGE_BATCH.md
**Content**: Migration from CompiledSession to ScheduledMessageBatch
**Status**: Still relevant but check if complete
**Action**: Review

#### docs/SUPERDIRT_MIGRATION_COMPLETE.md
**Date**: 2026-02-26
**Action**: Archive to docs/archive/

### Keep (Guides and References)

- docs/EXTENSION_DEVELOPMENT_GUIDE.md ✅
- docs/DISTRIBUTION_GUIDE.md ✅
- docs/LIVE_CODING_EXAMPLES.md ✅ (just created)
- docs/MIGRATION_GUIDE.md ✅ (just created)
- docs/SSE_EVENTS.md ✅ (just created)
- docs/USAGE_PATTERNS.md ✅
- docs/PERFORMANCE.md ✅

---

## scripts/ Directory Review

### Keep
- scripts/start-oiduna-api.sh ✅
- scripts/start_all.sh ✅
- scripts/demo_new_api.sh ✅
- scripts/README.md ✅

### Review
- scripts/integration-test.py - Check if still works
- scripts/test_assets.sh - Check if still relevant

---

## Action Plan

### Step 1: Critical Deletion
```bash
git rm GLOSSARY.md
```

### Step 2: Create Archive Directory
```bash
mkdir -p docs/archive
git mv PHASE_1_2_SUMMARY.md docs/archive/phase-1-2-summary.md
git mv PHASE_3_SUMMARY.md docs/archive/phase-3-summary.md
git mv ARCHITECTURE_REFACTORING_STATUS.md docs/archive/architecture-refactoring-status.md
git mv REVIEW_JP.md docs/archive/review-jp.md
git mv benchmark_plan.md docs/archive/benchmark-plan.md
git mv docs/SUPERDIRT_MIGRATION_COMPLETE.md docs/archive/superdirt-migration-complete.md
git mv docs/ARCHITECTURE_UNIFICATION_COMPLETE.md docs/archive/architecture-unification-complete.md
```

### Step 3: Update Current Docs
- IMPLEMENTATION_COMPLETE.md - Add ADR-0010 section
- REFACTORING_REPORT.md - Mark SessionManager split as complete
- COVERAGE_REPORT.md - Add integration test coverage
- TESTING_AND_QUALITY_SUMMARY.md - Update test counts

### Step 4: Verify docs/ Directory
- Review and update ARCHITECTURE.md
- Review and update DATA_MODEL_REFERENCE.md
- Verify API_REFERENCE.md accuracy
- Update OIDUNA_CONCEPTS.md if needed

### Step 5: Commit
```bash
git add -A
git commit -m "docs: cleanup outdated documentation and create archive

- Delete GLOSSARY.md (pre-SessionContainer, harmful if referenced)
- Archive phase summaries and old status docs
- Update current docs with ADR-0010 changes
- Organize historical documents in docs/archive/"
```

---

## Rationale

**Why Delete GLOSSARY.md?**
- Contains architecture that NO LONGER EXISTS (SessionManager Facade)
- No mention of SessionContainer or specialized managers
- API flow descriptions don't match current implementation
- Developer following this would write incorrect code
- Better to have no glossary than a harmful one

**Why Archive Phase Summaries?**
- Historical value for understanding project evolution
- But shouldn't clutter root directory
- Referenced in ADR docs for context

**Why Keep CLAUDE.md?**
- Updated 2026-02-28
- Actively used by Claude Code
- Contains correct information about current architecture

---

**Priority**: HIGH - GLOSSARY.md could cause significant confusion/bugs if referenced

**Estimate**: 30-60 minutes for full cleanup
