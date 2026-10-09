# Recovery review disposition — preview.3 source

Five substantive independent passes reviewed preview.2 commit `8d5c853`: journey correctness; evidence/privacy; comprehension/design; accessibility/startup; demo/regression/packaging. Three reviewers performed those passes without launching apps or scanning user files. Their original reports remain in the recovery handoff evidence.

## Material fixes

- Unknown individual file/error allocations now remain null/Unknown in folder browsing. Folder totals continue to sum only known allocation, with unknown/skipped counts. Regression first failed (0 instead of null), then passed.
- Folder aggregation collects each bucket's entry ID during its existing grouping and joins by primary key. This replaces an unindexed correlated lookup per bucket. A 12,000-row synthetic database query took 45.2729 seconds before and 0.0937 seconds after; the benchmark checks a five-second response budget. These are local observations, not a full-drive benchmark.
- Local access/enumeration errors receive coverage-gap guidance before cloud classification. The detail panel offers the recorded diagnostic secondarily. Regression first failed (cloud instead of coverage), then passed.
- Folder navigation clears stale rows and disables the old Up target while loading. Keyboard focus moves to the folder heading after results commit. File selection from either table focuses and scrolls to the updated detail panel after React commits it. The new delayed-response keyboard regression failed before the fix and passes after it.
- Root rows include their complete paths, and folder-name cells have room for those paths. This resolves ambiguous same-named roots and the inherited checkbox-column width.
- Recovery journey evidence now records the server's embedded build identity, version and supplied archive hash. Source-only results remain clearly distinct from exact-package results.

## Verification scope

30 focused Python tests passed. Three headless browser tests passed, including delayed folder responses, keyboard focus, diagnostic disclosure, real startup/picker lifecycle/drive selection and sample responsive behavior. Production TypeScript build passed. Headless browser use creates no visible app window.

The previously blocked independent security mutation probes were not rerun. Native user interaction stopped with Escape. No more visible app/browser launches, picker attempts, real C-drive scans or requests to repeat C selection are permitted under the current instruction. Only attributable isolated test sessions were gracefully shut down.

## Acceptance boundary

preview.2 is retained as a provisional superseded candidate, not published. Corrected preview.3 requires its own package hash and exact-package headless evidence. The historical preview.1 release remains immutable.

The observed preview.2 native Browse returned C:/ once, with a visible browser selection message. That observation does not prove native Cancel/retry/focus, a clean standard-user download/extraction/launch, or successful whole-C scan. These remain unverified. Under the master preview exception, the coordinator may consider a candid unsigned preview after material correctness checks; no stable claim is supported. Publication is held for coordinator review.
