# Clearspace implementation plan

Goal: a read-only Windows storage inventory and review planner, plus a fictional static sample.
Architecture: metadata adapter → streaming bounded SQLite scanner → deterministic policy and explicit duplicate stage → authenticated loopback FastAPI → React UI. Tk launcher owns process lifetime. No AI required.

## Constraints
No actual drive scans during development. Synthetic fixtures only. No deletion/move endpoints, cloud hydration, elevation, services, model downloads or arbitrary commands. Windows 11 x64 preview until clean standard-user acceptance. Named streams excluded explicitly. Unknown allocation is never zero. Source and private coordination stay separate.

## Tasks and gates
1. Metadata/scanner: `clearspace/metadata.py`, `inventory.py`, `policy.py`. `scan(roots, cancel)` stores identities, measurements and gaps; report/paged entries use decimal byte strings. Tests: overlapping roots, hardlinks, sparse >4GiB, Unicode, cancellation, budget, no content reads.
2. Duplicates/actions: `duplicates.py`, `server.py`. Selected ID groups only; bounded hash and byte comparison with before/after metadata, cloud/reparse exclusions. Token/Host/Origin gates and fixed settings destinations. Test hostile origins, unknown IDs, changing files and unequal bytes.
3. UI: React overview/map, sortable paged inventory, detailed review, Keep/later, scope/preflight, progress, rescan and export. Fictional data is always labelled; static build never probes localhost. Test sample interactions, mobile, keyboard, long filenames and exact integers.
4. Launcher/package: bundled frontend, Tk Open/Quit, singleton socket, readiness health check. Pinned PyInstaller one-folder. Test exact ZIP extracted under Unicode/spaces, startup/shutdown, API flow, no developer runtime requirement.
5. Five QC passes, public source audit, docs/evidence, draft then public unsigned preview, anonymous asset hash, static handoff.

Review focus: races through reparse ancestors; incomplete enumeration; allocation versus logical bytes; token leakage; stale duplicate claims. Native tests establish local Windows behavior only; cloud/clean-device checks remain pending unless actually performed.

Ruling: supplied complete design and explicit autonomous implementation/publication authorization supersede additional skill approval pauses. One owner; independent review requested through coordinator status.
