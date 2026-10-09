# Clearspace recovery candidate 0.1.0-preview.2

The preview.1 real-user journey failed acceptance. This candidate is not a completed release.

## Reproduced cause and changes

- The local browser initialized with fictional sample rows. Native startup now requests the real empty/saved inventory; sample is an explicit action.
- Browse called a blocking endpoint with a 120-second wait. The Windows dialog could be behind other windows, with no browser feedback and repeated requests queued. The request now returns immediately with a single-dialog lifecycle; the Tk owner is restored and raised, and cancellation/error/selection is polled visibly. Native focus acceptance remains required.
- Bare `C:` previously used Windows drive-relative resolution. It now means `C:\`. Blank and relative paths are rejected. Fixed drive buttons list roots without enumerating them; scanning requires Start.
- The flat list had no folder totals. A metadata-only folder view now aggregates recorded descendants, supports bounded pages and upward navigation, and sends file selections to the existing detail/review panel. Hard links are deduplicated within each displayed subtree; separate subtree totals may overlap.
- Starting a rescan immediately replaces the previous completion label with a pending state. Failed validation restores the prior inventory. Scan progress and cancellation retain partial results.

## Verification performed

- `python -m pytest tests/test_recovery.py tests/test_inventory.py tests/test_boundaries.py tests/test_regressions.py -q`: 28 passed.
- `npx playwright test --reporter=line`: real startup/picker lifecycle/drive selection and existing sample responsive flow passed (2 tests).
- `npm run build`: TypeScript and production build passed.
- `node scripts/test_recovery_journey.mjs work/recovery-finaldata/session.json`: real local startup, invalid path feedback, synthetic metadata scan, nested folder navigation, file detail + Keep, upward navigation, saved inventory reload, mobile width, visible scan progress and cancellation passed. This exercises the ordinary launcher URL in Edge without injected API headers. It does NOT certify native Browse.
- Native inspection found the original dialog nested under the launcher. Desktop input interrupted the repaired Cancel/Select checks; those checks are pending and must not be inferred from mocks.

## Remaining acceptance

1. Native foreground dialog, Cancel, retry, selection and repeated Browse on the exact extracted new ZIP.
2. Exact package headless/browser checks, five substantive journey QC records, artifact hashes and coordinator intake.
3. No publication until native acceptance is complete. Keep the immutable preview.1 assets intact.

No real user drive was scanned during recovery; only workspace fixtures. Existing user launcher/data were preserved. Previously filtered mutation rechecks were not retried. No model, telemetry, deletion, service or startup entry was added.
