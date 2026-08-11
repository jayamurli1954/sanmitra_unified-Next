# ADR-013: OfficeMitra workflow template library

**Status:** Future  
**Date:** 2026-08-07  
**Product scope:** OfficeMitra AI experience expansion  
**Depends on:** Accepted [ADR-009](ADR-009-officemitra-workflow-engine.md)  
**Related:** [ADR-011](ADR-011-officemitra-domain-events.md)  

## Context

ADR-009 separates workflow templates from runs. Over time, SanMitra will want curated templates (“Daily follow-up”, “Meeting wrap-up”) and possibly tenant-shared libraries. A marketplace-style distribution model is premature before the engine exists.

## Decision (intent only)

1. Maintain a **versioned template library** (system defaults + tenant custom templates).
2. Templates reference only Action Registry `action_type` keys and Capability Descriptor constraints.
3. Marketplace / cross-tenant publishing is deferred until governance, licensing, and safety review exist.
4. This ADR remains **Future** until ADR-009 is Accepted and at least one production template has run in staging. (ADR-009 is Accepted; Phase 6 engine exists — curated library / marketplace still Future.)

## Consequences

- Do not build marketplace UI in Phase 6.
- Document system templates alongside ADR-009 implementation when Accepted.
