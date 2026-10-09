"""Bounded synthetic benchmark; no actual user-drive scan."""
import json
import threading
import time
import tracemalloc
from pathlib import Path
from clearspace.inventory import Inventory

base=Path('work/benchmark-fixture').absolute();root=base/'selected';root.mkdir(parents=True,exist_ok=True)
for n in range(10000):(root/f'fixture-{n:05d}.txt').touch()
inv=Inventory(base/'app-data')
tracemalloc.start();start=time.perf_counter();inv.scan([str(root)],threading.Event());elapsed=time.perf_counter()-start
report=inv.report();current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
result={'fixture':'10000 empty ordinary files, no user data','items':report['items'],'status':report['status'],'seconds':round(elapsed,3),'python_tracemalloc_peak_bytes':peak,'inventory_bytes':inv.db.stat().st_size,'limitation':'Python allocation trace excludes native SQLite/Windows/runtime memory; not a whole-volume benchmark'}
Path('outputs/benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
