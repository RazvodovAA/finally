# FinAlly E2E Testing - Quick Start

**Status**: Phase 4 testing infrastructure is complete and ready.

This is the quick reference. For details, see:
- **Full guide**: `planning/PHASE4_E2E_TESTING.md`
- **Setup details**: `planning/PHASE4_SETUP_SUMMARY.md`
- **Bug tracking**: `planning/BUGS.md`
- **Test README**: `test/README.md`

---

## Run Tests Now

### Option 1: Docker (Recommended)
```bash
cd /Users/antonrazvodov/projects/finally
./test/run.sh
```

### Option 2: Local
```bash
cd /Users/antonrazvodov/projects/finally/test
npm install
npx playwright test
```

### Option 3: View Results
```bash
npx playwright show-report
```

---

## Test Categories

| Category | Tests | Status | Trigger |
|----------|-------|--------|---------|
| Smoke | 5 | ✓ Working | `./test/run.sh` |
| Watchlist | 10 | 📋 Framework ready | `npx playwright test --grep "watchlist"` |
| Trading | 20+ | 📋 Framework ready | `npx playwright test --grep "trade"` |
| Portfolio | 18 | 📋 Framework ready | `npx playwright test --grep "portfolio"` |
| Chat | 20 | 📋 Framework ready | `npx playwright test --grep "chat"` |
| SSE | 25+ | 📋 Framework ready | `npx playwright test --grep "stream"` |
| Error | 30+ | 📋 Framework ready | `npx playwright test --grep "error"` |

---

## Docker Execution

```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit
```

This:
1. Builds Dockerfile (Node → Python)
2. Starts API container on port 8000
3. Waits for health check to pass
4. Runs Playwright tests
5. Exits with test status (0=passed, 1=failed)

---

## File Structure

```
test/
├── .gitignore
├── README.md                 ← Full testing guide
├── run.sh                    ← Test runner (executable)
├── package.json              ← Playwright dependency
├── playwright.config.ts      ← Playwright config
├── docker-compose.test.yml   ← Test environment
└── specs/
    ├── smoke.spec.ts         ← 5 basic tests (WORKING)
    ├── watchlist.spec.ts     ← Watchlist tests
    ├── trading.spec.ts       ← Trading tests
    ├── portfolio.spec.ts     ← Portfolio tests
    ├── chat.spec.ts          ← Chat tests
    ├── sse.spec.ts           ← Streaming tests
    └── error.spec.ts         ← Error tests

planning/
├── PLAN.md                   ← Project spec
├── PHASE4_E2E_TESTING.md     ← Complete guide
├── PHASE4_SETUP_SUMMARY.md   ← Setup details
├── BUGS.md                   ← Bug tracker
└── TESTING_QUICK_START.md    ← This file
```

---

## Common Commands

### Run All Tests
```bash
./test/run.sh
```

### Run Specific Category
```bash
npx playwright test --grep "watchlist"
npx playwright test --grep "trade"
npx playwright test --grep "error"
```

### Debug Mode
```bash
./test/run.sh --debug
```

### See Browser
```bash
./test/run.sh --local --headed
```

### Interactive UI
```bash
./test/run.sh --ui
```

### View Report
```bash
npx playwright show-report
```

### Clean Up Docker
```bash
./test/run.sh --clean
```

---

## Test Readiness

### Now (Smoke Tests)
✓ Page loads
✓ API health
✓ Endpoints reachable
✓ SSE available

**Ready to run immediately**

### Phase 3 Completion (Feature Tests)
Watchlist, Trading, Portfolio, Chat, SSE, Error handling

**Will activate as frontend is built**

---

## Bug Tracking

Found a bug? Log it:

1. Open `planning/BUGS.md`
2. Add entry with:
   - Title
   - Description
   - Steps to reproduce
   - Expected vs actual
   - Component (Frontend/Backend/Market Data/Chat)
   - Severity (P0-P3)
3. Assign to responsible agent
4. Link to test that fails
5. Update status when fixed

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `test/run.sh` | Execute tests (local or Docker) |
| `test/docker-compose.test.yml` | Test environment |
| `test/specs/*.spec.ts` | Test definitions |
| `planning/BUGS.md` | Bug tracking |
| `planning/PHASE4_E2E_TESTING.md` | Complete testing guide |

---

## Quick Links

- **Test command**: `./test/run.sh`
- **Full guide**: `/Users/antonrazvodov/projects/finally/planning/PHASE4_E2E_TESTING.md`
- **Test specs**: `/Users/antonrazvodov/projects/finally/test/specs/`
- **Bug report**: `/Users/antonrazvodov/projects/finally/planning/BUGS.md`

---

## What's Next?

1. **Now**: Run smoke tests
   ```bash
   ./test/run.sh
   ```

2. **After Phase 3**: Feature tests become active
   - Frontend team completes components
   - Test specs updated with real selectors
   - Run full suite

3. **During testing**: File bugs
   - Log issues to `BUGS.md`
   - Assign to team
   - Verify fixes

4. **Release**: All tests passing
   - Zero P0 bugs
   - < 5 P1 bugs
   - Full coverage

---

## Support

For questions on:
- **How to run tests**: See `test/README.md`
- **What tests do**: See `planning/PHASE4_E2E_TESTING.md`
- **Full details**: See `planning/PHASE4_SETUP_SUMMARY.md`
- **Bug process**: See `planning/BUGS.md`

**Status**: Phase 4 is ready. Infrastructure working. Smoke tests passing.
