# Clearspace recovery candidate 0.1.0-preview.3

The preview.1 real-user journey failed acceptance. Corrected preview.3 is an unsigned preview candidate with completed exact-package headless checks and explicit remaining desktop acceptance gaps. Publication is held for coordinator review under the master-approved candid-preview exception.

## Reproduced cause and changes

- The local browser initialized with fictional sample rows. Native startup now requests the real empty/saved inventory; sample is an explicit action.
- Browse called a blocking endpoint with a 120-second wait. The Windows dialog could be behind other windows, with no browser feedback and repeated requests queued. The request now returns immediately with a single-dialog lifecycle; the Tk owner is restored and raised, and cancellation/error/selection is polled visibly. Native focus acceptance remains required.
- Bare `C:` previously used Windows drive-relative resolution. It now means `C:\`. Blank and relative paths are rejected. Fixed drive buttons list roots without enumerating them; scanning requires Start.
- The flat list had no folder totals. A metadata-only folder view now aggregates recorded descendants, supports bounded pages and upward navigation, and sends file selections to the existing detail/review panel. Hard links are deduplicated within each displayed subtree; separate subtree totals may overlap.
- Starting a rescan immediately replaces the previous completion label with a pending state. Failed validation restores the prior inventory. Scan progress and cancellation retain partial results.

## Verification performed

- `python -m pytest tests/test_recovery.py tests/test_inventory.py tests/test_boundaries.py tests/test_regressions.py -q`: 30 passed.
- `npx playwright test --reporter=line`: delayed folder loading/keyboard focus, real startup/picker lifecycle/drive selection and sample responsive flow passed (3 tests).
- `npm run build`: TypeScript and production build passed.
- `node scripts/test_recovery_journey.mjs work/recovery-finaldata/session.json`: real local startup, invalid path feedback, synthetic metadata scan, nested folder navigation, file detail + Keep, upward navigation, saved inventory reload, mobile width, visible scan progress and cancellation passed. This exercises the ordinary launcher URL in Edge without injected API headers. It does NOT certify native Browse.
- Exact preview.3 extracted executable: all 1,107 extracted files match the ZIP; embedded source identity matches. Headless API flow passed 1,503 synthetic items, export, main-stream duplicate comparison, remeasure, cancellation, duplicate-launch refusal, graceful shutdown and Keep persistence after restart. Headless browser flow passed real startup, invalid path feedback, synthetic scan, nested navigation, details/Keep, Up, reload, mobile width and cancellation. Evidence records the exact archive SHA-256 and embedded build identity.
- Five substantive independent review passes completed. Their material source findings were fixed: unknown allocation, quadratic folder query, error guidance, stale navigation/focus and evidence identity. A 12,000-row synthetic query improved from 45.2729s to 0.0937s; this is not a full-drive benchmark. See `RECOVERY_REVIEW_FIXES.md` and the versioned handoff for findings and disposition.
- Earlier preview.2 native Browse returned `C:/` once with visible selection feedback. A second attempt was physically stopped with Escape. This does not establish preview.3 native acceptance. The user then explicitly stopped repeated app/site launches and C-drive selection requests. Corrected preview.3 packaging and checks used only headless processes and synthetic workspace fixtures.

## Exact candidate identity

- Tested binary source: `26913833a3652ae61156a0f201124430c6aca0ba`. Later documentation-only commits do not change this binary identity.
- ZIP: `Clearspace-0.1.0-preview.3-windows-x64.zip`
- SHA-256: `3196f03e5646d8954e403f268ac893bb5aeaf5d0eb42850a05c7616264216aaf`
- Versioned owner evidence: `outputs/0.1.0-preview.3/`; full `HANDOFF.md`, manifests, exact-package results, reviews and cleanup record.
- Static sample SHA-256: `39fabb7ba79dd9528b653360d4a1a0c96347b5fa6e1a8c29d7a76607bbc0b9aa`, base `/tools/clearspace/`. Fictional sample; cannot scan local files.

## Remaining acceptance

1. Native foreground dialog, Cancel/retry, selection, repeated Browse, launcher Open/Quit and Open containing folder/manual review/rescan on exact preview.3 remain unverified.
2. Clean standard-user browser download/Extract all/launch and successful whole-C scanning remain unverified. Do not restart visible/native testing or request another C selection without new direct user authorization.
3. Coordinator review may accept an explicitly limited unsigned preview despite these native gaps under the master preview exception. No stable or fully verified Windows claim is supported. Publication has not occurred; preserve immutable preview.1 assets and superseded preview.2 evidence.

No real user drive was scanned during recovery; only workspace fixtures. Existing user launcher/data were preserved. Previously filtered mutation rechecks were not retried. No model, telemetry, deletion, service or startup entry was added.
