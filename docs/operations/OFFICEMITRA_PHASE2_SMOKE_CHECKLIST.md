# OfficeMitra AI — Phase 2 Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 2 / Productivity depth (Calendar + Meeting Notes + Notifications)  
**Date:** 2026-08-05  
**Depends on:** Phase 1 smoke signed off (`docs/operations/OFFICEMITRA_PHASE1_SMOKE_CHECKLIST.md`)  
**ADRs:** ADR-001 … ADR-007  

## Enable a demo tenant

1. Tenant has `office_ai` in `enabled_modules` (parent alone enables all Phase 2 flags).
2. Optional granular flags: `office_ai.calendar`, `office_ai.meeting_notes`, `office_ai.notifications`.
3. No Google/Outlook OAuth required — paste-in only.
4. AI key optional; soft-fail / deterministic calendar parse still pass.

## UI smoke (MitraBooks shell → OfficeMitra AI)

### Calendar

- [ ] Tab **Calendar** visible
- [ ] Paste agenda lines (e.g. `10:00 GST review`) → **Parse + save events**
- [ ] Today’s events table shows saved rows
- [ ] Optional: paste ICS `BEGIN:VEVENT` block → events appear

### Meeting Notes

- [ ] Tab **Meeting Notes** visible
- [ ] Paste notes → **Summarize + suggest tasks**
- [ ] Soft-fail notice OK without API key; note still listed
- [ ] When AI available, suggested tasks appear under **Tasks**

### Notifications

- [ ] Tab **Notifications** visible (unread badge may show)
- [ ] Calendar save and/or note process creates inbox rows
- [ ] **Mark read** updates row; unread count decreases

### Today Brief

- [ ] **Generate today’s brief** includes `today_calendar` / meeting-note sections when data exists (fallback OK)
- [ ] Brief-ready notification may appear

## Isolation / safety

- [ ] Tenant A cannot see Tenant B calendar / notes / notifications
- [ ] No OAuth calendar connectors
- [ ] No journal / invoice write paths from OfficeMitra

## Exit criteria (Phase 2)

- [ ] Three Phase 2 features usable on a demo tenant
- [ ] Phase 1 features still work
- [ ] ADR-001…007 respected; InvestMitra untouched
- [ ] `pytest tests/test_office_ai*.py` green locally
