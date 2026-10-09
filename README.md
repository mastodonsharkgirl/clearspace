# Clearspace

**Find the space. Understand the trade-off. Choose what goes.**

A local Windows disk-space planner with a browser interface. It inventories metadata, explains uncertainty and helps you review files through Windows. It never deletes or moves files. No model, account, paid API or administrator setup is required for core use.

## Windows preview

1. Download the versioned Windows x64 ZIP from [Releases](https://github.com/mastodonsharkgirl/clearspace/releases).
2. Use **Extract all**, keeping the complete folder together.
3. Open **Clearspace.exe**, then choose a folder in the browser.

Use **Open Clearspace** and **Quit Clearspace** in the launcher. Closing a browser tab does not stop the app. The browser also supports the authenticated quit endpoint for development tests. No service or startup entry is installed.

This release is **unsigned preview software**, targeting Windows 11 x64. SmartScreen or other normal Windows protections may warn or block it. Do not disable protections to run it. Clean standard-user browser download / Extract all / launch acceptance on a desktop without developer tools is **pending**. Checksums establish file identity, not trust or safety.

## What is implemented

- Streaming metadata enumeration into SQLite, with item and storage limits, progress, cancellation and usable partial results.
- NTFS ordinary-file allocation through `FILE_STANDARD_INFO.AllocationSize`; compressed/sparse default-stream storage through `GetCompressedFileSizeW`. Logical file length is separate. Unknown allocation remains unknown.
- Known hard-link allocation counted once, with all names preserved. Shared allocation is excluded from reviewable totals.
- Reparse points, mount links and possible cloud placeholders excluded. Named NTFS streams and filesystem metadata are explicitly outside accounting scope.
- Category map, sortable paginated table, exact byte details, Keep / Review later, protected-folder rules, containing-folder and fixed Windows-settings handoffs.
- Separate selected-file SHA-256 + final streamed byte comparison. Main stream only, with metadata rechecks and no-write-share read handles. No autonomous keeper/deletion decision.
- Timestamped before/after volume observations, export of the private plan, and rescan with Keep choices retained by path.
- Fictional static explorer, with no probing of local services or visitor drives.

**Not implemented:** deletion, moving, Recycle Bin execution, cloud dehydration, automatic cleanup, AI inference or LangChain/RAG. The guidance panel uses authored source-backed templates. A simulated rejected suggestion tests a deterministic boundary; it is not an AI benchmark. These extensions do not gate the core release.

## Scope and limitations

Choose ordinary fixed local folders. NTFS is the supported allocation target. Other filesystems have reduced/unknown allocation. Junctions and links are not traversed. Scan errors and exclusions make coverage partial. Permission failures do not mean empty folders. This is not a filesystem snapshot: concurrent changes can make observations stale. Re-scan before acting.

Known allocation covers file default streams, not directories, named streams, NTFS metadata or every system allocation. The volume remainder includes outside-scope, system and inaccessible space; it is not evidence of corruption. Volume capacity/available space can reflect caller quotas. Reviewable allocation is not safe savings. Same-volume Recycle Bin moves generally retain space; cross-drive moves shift occupancy.

The metadata stage does not read document contents. OneDrive hydration prevention has conservative logic tests but **physical OneDrive placeholder non-hydration testing remains pending**. Cross-volume junction, genuine permission/lock races and clean-device GUI acceptance have limits documented in `docs/VALIDATION.md`.

## Local data and bounds

Default app directory: `%LOCALAPPDATA%\Clearspace`. The UI displays its location, available bytes, 256 MiB inventory-plus-journal budget, 512 MiB free-space reserve and 500,000-item cap before scanning. Half the budget is reserved for a rollback journal. Directory queues are stored in SQLite. Content comparisons read at most 2 GiB per operation, with at most 100 selected IDs. App inventory data is excluded from scans. To choose another dedicated data directory, use the launcher's data-location button; it restarts the app there.

Quit first. To clear only Clearspace data, remove **only the displayed dedicated Clearspace app directory**, after checking you have not placed personal files there. This removes inventory and review choices. Never delete a scan root as an app-reset action. Exports contain full private paths; review before sharing.

Updates are manual. Keep old ZIPs for rollback. Preview database schema is version 1; back up the app directory before changing versions. Do not run different versions against the same directory simultaneously.

## Development

Windows, Python 3.13 x64, Node 24.11 or compatible Vite-supported version:

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock
npm ci
npm run build
.venv/Scripts/python.exe run_clearspace.py
```

```powershell
.venv/Scripts/python.exe -m pytest -q
npx playwright test
npm run build:sample
.venv/Scripts/python.exe scripts/test_package.py .venv/Scripts/python.exe --source
```

Tests only scan generated fixtures under `work/`. Browser tests use installed Microsoft Edge. Static output uses `/tools/clearspace/`; serve it under that prefix. No model weights or external fonts are fetched.

See [architecture](docs/ARCHITECTURE.md), [validation](docs/VALIDATION.md), [reviews](REVIEW_LOG.md), [learning guide](LEARNING_GUIDE.md) and [demo](docs/DEMO.md). Source and implementation were generated/edited with Codex assistance; product constraints were supplied by the project owner. Generated code is not evidence of independently completed learner exercises.
