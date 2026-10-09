# Learn from the shipped Clearspace code

Prepared for later study. No learner exercises are recorded as completed. Product requirements and boundaries were supplied by the owner; implementation and tests were generated/edited with Codex assistance.

## 1. Iteration and dictionaries
User value: a folder can contain more files than fit comfortably in memory. `Inventory.scan` consumes `os.scandir` entries progressively and puts directory work in SQLite. A metadata dictionary keeps names attached to values, for example `{'logical': 5001, 'allocated': 8192}`. Exercise: write a small script that counts three synthetic files without reading them. Predict the result first.

## 2. Metadata versus contents
`metadata.metadata` reads identity, attributes and sizes. `duplicates.compare_selected` explicitly reads contents. A 5,001-byte file can occupy 8,192 bytes; a sparse 5 GiB file can have no allocated data. Exercise: explain why logical length and disk usage can differ. Locate the ordinary, compressed and sparse branches. Do not use personal files for the exercise.

## 3. SQLite and durable state
`Inventory.connect` is a context manager that commits/rolls back and explicitly closes the database. SQLite's own context manager does not close it automatically. Exercise: explain the regression test that checks a closed connection. Add a synthetic Keep choice, rescan, and explain why the path retains it.

## 4. HTTP and a local browser
The launcher owns a loopback server. React requests pages of records; it cannot directly scan a native Windows drive. A session token protects the API, and Host/Origin checks narrow who can call it. Exercise: trace Choose folder → `POST /api/scan` → scanner → `GET /api/report` → map. Explain why an exported plan can contain private paths even though no data is uploaded.

## 5. Duplicate proof and uncertainty
A matching size is only a candidate. A cryptographic hash reduces comparisons; the final streamed byte comparison confirms the compared main streams at that time. Hardlinks share allocation and are excluded from independent duplicate claims. Exercise: create two three-byte fixtures with unequal contents and predict the result. Explain why equal contents do not prove either copy is unnecessary.

## 6. Embeddings, retrieval, RAG and bounded classification
These are concepts, **not implemented integrations in this release**. Embeddings represent text for similarity search. Retrieval selects guidance; RAG adds a generator using that guidance as context. LangChain could compose those steps but is not needed for exact byte arithmetic. Clearspace currently selects authored cards using deterministic categories. `validate_advice` is a simulated policy-boundary fixture, not a model call. Exercise: write down which fields a future model must never control: protected status, paths, actions, duplicate proof and savings arithmetic. Explain how Unknown should work when a model is unavailable or uncertain.

## 7. A real failure investigation
The first allocation implementation used GetCompressedFileSizeW for ordinary files. An independent review checked Microsoft remarks; a 5,001-byte physical fixture then demonstrated that the returned length was not allocation. The corrected ordinary branch uses FILE_STANDARD_INFO. The sparse test also exposed CRT truncate zero-filling; native SetFilePointerEx/SetEndOfFile preserved the hole. Exercise: explain the difference between a product defect and a defective test fixture, and why comparing an adapter to itself was insufficient.

## 8. Packaging and releases
PyInstaller one-folder bundles Python and the compiled UI. The package must be tested after ZIP extraction because source tests do not prove frozen imports, startup or shutdown. A checksum identifies bytes; an unsigned binary has no publisher signature. Exercise: verify a downloaded ZIP hash and explain why this is still not the same as standard-user device acceptance.

## Hints (read after trying)
1: `os.scandir` yields one entry at a time. 2: allocation is the storage reserved locally. 3: closing belongs in `finally`. 4: look at `create_app` routes. 5: size/hash/compare answer different questions. 6: code keeps authority. 7: use an independent oracle. 8: source, build environment and exact artifact are separate evidence.

## Suggested solutions (keep separate from attempts)
Counting: `sum(1 for entry in os.scandir(fixture) if entry.is_file(follow_symlinks=False))`. A local token cannot prove the machine is malware-free; it prevents unauthenticated websites from using these endpoints. Duplicate equality applies to a stream, not ownership. Stable acceptance must include the actual downloaded artifact with normal Windows protections unchanged.
