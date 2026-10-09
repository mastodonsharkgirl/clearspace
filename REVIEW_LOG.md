# Review log

Five passes are scoped to implemented no-model functionality. The implementation owner performed local tests and visual inspection. Coordinator feedback is independent read-only review; a further reviewer was requested and remains pending until its report is received. No fabricated reviewers or hardware acceptance.

## Pass 1 — product usefulness / first use
Issue: logical and allocated sizes were easy to conflate; tiny native files displayed as zero GiB. Fix: distinct metrics, exact byte detail and adaptive binary units. The sample always labels fiction, partial coverage and no device scan. Keep removes a candidate from reviewable allocation; recovery is never claimed. Recheck: desktop/mobile Playwright flow covers Keep, app handoff, cloud guidance and no page errors; native source end-to-end scans 1,503 synthetic items and exports 1,504 NDJSON lines.

## Pass 2 — Windows measurement / coverage
Independent coordinator finding: GetCompressedFileSizeW returns ordinary file length, not correct allocation. Failing physical 5,001-byte fixture proved the issue. Fix: FILE_STANDARD_INFO allocation for ordinary files; compressed/sparse branch retained. Recheck: ordinary allocation >=8,192, compressed 1 MiB fixture occupies less, sparse >5 GiB default stream occupies zero; long Unicode paths and junction cycle test pass. Unknown identity roots no longer collapse. Named-stream/filesystem metadata exclusion is explicit. A faulty CRT sparse fixture temporarily allocated data; the disposable fixture was removed and native end-of-file APIs replaced it. Physical OneDrive non-hydration remains pending.

## Pass 3 — local privacy / actions / AI boundaries
Independent coordinator findings: SQLite context managers did not close connections; export could mix scans; unhandled worker exceptions could expose paths. Fixes: explicit close, stream lifetime action lock and terminal partial state without traceback. Rechecks: closed-connection assertion, export lock inspection, token/Host/Origin denial, oversized body, invalid settings/action IDs, stale scan ID, no delete endpoint, hardlink duplicate exclusion and policy rejection fixture. Fixed settings URLs checked against official docs. No model is integrated, so model/RAG behavior is not claimed.

## Pass 4 — visual/accessibility/performance/storage
Issue: narrow map labels wrap heavily; category legend and sortable table provide the same accessible data. Map remains a labelled allocation strip/treemap, with unknowns outside the area calculation. No color-only meaning. UI uses keyboard controls and focus rings; reduced-motion rules disable animation. Real 1440px and 390px screenshots inspected, no horizontal document overflow in the browser test. Paginated table caps rendering; idle report caching prevents repeated aggregation. SQLite reserves half of total budget for rollback journal; low-free-space fixture stops with partial report. Large inventory runtime and packaged cold-start evidence are recorded separately, not inferred from screenshots.

## Pass 5 — fresh artifact / release integrity
In progress: source end-to-end passed duplicate launch, synthetic scan, comparison, export, cancellation, graceful shutdown, restart and Keep persistence. Package must pass the same flow after exact ZIP extraction before release. Public source audit, notices/SBOM, artifact hashes, anonymous redownload and static base-path handoff remain required. Clean standard-user desktop/browser-origin acceptance remains pending, so release stays unsigned preview.
