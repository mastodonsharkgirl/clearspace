# Validation status

Target: Windows 11 x64. Development host: Windows 11 Home build 10.0.26200 with developer tools installed. This is not a clean standard-user acceptance environment.

Source tests cover 30 cases including independent-review regressions: overlap, metadata without content opens, hardlinks, cancellation/budget, unknown allocation, actual ordinary NTFS allocation, explicit DB closing, actual duplicates versus unequal same-size files, changed files, endpoint boundaries, physical sparse >4 GiB, compressed files, long Unicode paths, junction cycle, low storage, simulated cloud flags, missing identity, >2^53 JSON fidelity, simulated permission gaps, export consistency and invalid actions. Actual results are saved in release evidence; counts may increase with review fixes.

Browser evidence: Edge, desktop 1440×1000 and mobile viewport 390×844, sample Keep/app/cloud flow, screenshot capture and document overflow check. Viewport simulation is not a physical phone test.

Source end-to-end: 1,503 generated items, confirmed identical main-stream group, 1,504-line export, cancel retaining partial inventory, timestamped remeasurement, singleton rejection, graceful shutdown, restart with Keep persistence. App data measured about 1.6 MiB for that fixture; this is not a million-file benchmark.

Pending physical coverage: OneDrive placeholder non-hydration; cross-volume mount on a dedicated fixture; live permission/lock/rename races beyond deterministic simulations; full-volume scale; clean standard-user Windows download in browser, Extract all and launch with normal protections unchanged. Optional AI is absent, not a passed pending feature.

Security scope: local browser access control, fixed actions and read-only source operations. Same-user malware and filesystem races are not eliminated. Keep results uncertainty-qualified and rescan after changes.

Synthetic scale check: 10,001 items (10,000 empty files) completed in 13.882 seconds with Python tracemalloc enabled; peak traced Python allocations 1,758,669 bytes and inventory file 10,899,456 bytes. Reusing native metadata bindings reduced this from the 80.693-second traced baseline. These are one-host fixture observations, not whole-volume guarantees; native runtime memory is excluded from tracemalloc.


Final independent recheck of the in-place reparse fix was unavailable due an environment filter; the owner regression passed. This does not establish independent final approval. The earlier independent review and its findings are retained in REVIEW_LOG.md.

