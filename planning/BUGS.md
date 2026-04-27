# Bug Tracker

Log of bugs found during Phase 4 E2E testing, their status, and resolution.

## Format

```
## [P0/P1/P2/P3] Title

**Component**: Frontend / Backend API / Market Data / Chat / Database
**Status**: Open / In Progress / Fixed / Blocked / Wontfix
**Assigned To**: @[agent-name]
**Created**: YYYY-MM-DD
**Resolved**: YYYY-MM-DD

**Description**:
What is broken.

**Steps to Reproduce**:
1. ...
2. ...
3. ...

**Expected Behavior**:
What should happen.

**Actual Behavior**:
What actually happens.

**Root Cause**:
(Filled in after investigation)

**Logs/Evidence**:
```
Code snippet, error message, screenshot, etc.
```

**Fix Applied**:
(Filled in when resolved)

---
```

## Active Bugs

(None yet — Phase 4 testing in progress)

## Resolved Bugs

(None yet)

## Known Limitations

These are not bugs, but expected gaps pending Phase 3 completion:

1. **Frontend not yet functional** — Phase 3 in progress
   - Watchlist UI not implemented
   - Trading form not implemented
   - Portfolio visualization not implemented
   - Chat panel not implemented
   - Price flash animations not implemented
   - Connection status indicator not implemented

2. **Chat API not yet implemented** — Phase 3 in progress
   - `POST /api/chat` endpoint not created
   - LLM response parsing not implemented
   - Trade auto-execution not implemented

3. **Portfolio snapshots not seeded** — Minor
   - P&L chart has no initial data point
   - Should seed one snapshot on fresh start with portfolio value = cash_balance

---

## Triage Process

When a test fails or a bug is reported:

1. **Reproduce** — Run the failing test locally, confirm consistent reproduction
2. **Isolate** — Determine which component(s) are responsible
3. **Evidence** — Collect logs, screenshots, network traces
4. **File** — Create bug entry in this document with details above
5. **Assign** — Tag responsible team member
6. **Fix** — Team member investigates root cause and applies fix
7. **Verify** — Re-run test to confirm fix
8. **Close** — Update bug status to "Fixed" and resolved date

---

## Bug Statistics

| Severity | Open | In Progress | Fixed | Total |
|----------|------|-------------|-------|-------|
| P0       | 0    | 0           | 0     | 0     |
| P1       | 0    | 0           | 0     | 0     |
| P2       | 0    | 0           | 0     | 0     |
| P3       | 0    | 0           | 0     | 0     |
| **Total**| **0**| **0**       | **0** | **0** |
