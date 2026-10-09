# Architecture and trust boundaries

`metadata.py` reads attributes, identities and allocation. `inventory.py` iterates directory entries, queues directories in SQLite, batches writes and serializes safe decimal byte strings. `policy.py` classifies conservatively. `duplicates.py` alone reads content, after explicit selected IDs. `server.py` resolves item IDs and exposes a narrow API. `launcher.py` owns the loopback socket, session token, worker shutdown and Tk controls. React is presentation; all real inventory arithmetic is Python/SQLite, with BigInt display calculations.

The server binds only 127.0.0.1. Exact Host, same Origin when supplied, cross-site fetch checks and a random per-session token protect every inventory endpoint. Tokens arrive in a URL fragment, are removed from the address bar and kept in that tab's session storage. Access logging is off. There is no wildcard CORS, telemetry, arbitrary shell endpoint or local file-serving route. Static serving is restricted to compiled frontend assets.

Folder opening accepts an inventory ID and scan ID, revalidates metadata and ordinary ancestors, checks the containing folder is within scope, then uses a structured `explorer.exe` argument. Windows settings use a two-entry fixed URI map. The operating system remains responsible for any cleanup. This does not defend against a malicious program already executing as the same Windows user.

SQLite connections explicitly close. Exports hold an operation lock until the stream closes, preventing scan replacement during export. Scan failures become partial state without path tracebacks. Reports are cached by scan state/review revision, avoiding repeated aggregation when idle. Memory is bounded by the configured inventory cap; reports use a set of known identities up to that cap. Page rendering is capped at 100 entries, normally 50.

A scan enumerating its scope successfully is labelled complete even though documented exclusions such as named streams and filesystem metadata remain outside its measurement definition. Detected access/link/cloud gaps produce partial status. Allocation is not complete volume accounting.

## Official compatibility references (checked 9 October 2026)

- [FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info): ordinary allocation field.
- [GetCompressedFileSizeW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getcompressedfilesizew): compressed/sparse storage; ordinary-file return is logical length, which is why that branch uses a different API.
- [GetDiskFreeSpaceExW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskfreespaceexw): free versus caller-available bytes, quota caveats.
- [Reparse points](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points): exclusion boundaries.
- [Settings URIs](https://learn.microsoft.com/en-us/windows/apps/develop/launch/launch-settings): `ms-settings:storagesense`, `ms-settings:appsfeatures`.
- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/), [PyInstaller one-folder](https://pyinstaller.org/en/stable/operating-mode.html).

No AI model is bundled or integrated. `MODEL_MANIFEST.json` makes the absence explicit. A future optional extension requires its own footprint, license, stability and Windows tests; model output must never create paths/actions or override protected rules.
