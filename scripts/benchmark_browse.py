import json,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clearspace.inventory import Inventory
root='C:\\ClearspaceSynthetic\\Root'
base=Path('work')/('browse-benchmark-'+uuid.uuid4().hex)
inv=Inventory(base)
state={'status':'complete','items':12001,'roots':[root],'gaps':0,'scan_id':'synthetic-benchmark'}
with inv.connect() as c:
    for index in range(12001):
        folder=index==0
        m=dict(path=root if folder else root+f'\\synthetic-{index:05}.bin',parent=str(Path(root).parent) if folder else root,kind='directory' if folder else 'file',logical=0 if folder else index,allocated=None if folder else index,identity=str(index),links=1,reparse=False,cloud='ordinary-local',allocation_status='synthetic',error=None)
        inv.record(c,{'items':0},m,())
    inv.save_state(c,state)
start=time.perf_counter();rows=inv.browse(root);elapsed=time.perf_counter()-start
assert len(rows['entries'])==50 and rows['has_more']
assert int(rows['entries'][0]['allocated'])==12000
result={'dataset':'12000 synthetic database file rows; no real files scanned','seconds':round(elapsed,4),'response_budget_seconds':5,'returned':len(rows['entries']),'largest':rows['entries'][0]['allocated']}
print(json.dumps(result))
assert elapsed<5, 'Folder page exceeded the five-second synthetic response budget'
