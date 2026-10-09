"""Run against an extracted release; all scans confined to work/package-fixtures."""
import argparse
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('exe');p.add_argument('--source',action='store_true');args=p.parse_args()
base=Path('work/package-fixtures').absolute();base.mkdir(parents=True,exist_ok=True)
data=base/'app data ü';root=base/'Downloads';root.mkdir(exist_ok=True)
for n in range(1500): (root/f'fictional-{n}.txt').write_text('fixture '+str(n))
(root/'copy-a.bin').write_bytes(b'abc'*5000);(root/'copy-b.bin').write_bytes(b'abc'*5000)
command=([args.exe,'run_clearspace.py'] if args.source else [args.exe])+['--headless','--data',str(data)]
def launch():
    process=subprocess.Popen(command)
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError(f'Premature exit {process.returncode}')
        session=data/'session.json'
        if session.exists():
            value=json.loads(session.read_text());url=value['url'];base_url=url.split('/#')[0];token=url.split('token=')[1]
            try:
                urllib.request.urlopen(base_url+'/health',timeout=1).close();return process,base_url,token
            except OSError:pass
        time.sleep(.1)
    raise RuntimeError('Startup timeout')
process,base_url,token=launch()
def api(path,body=None):
    request=urllib.request.Request(base_url+'/api/'+path,data=None if body is None else json.dumps(body).encode(),headers={'X-Clearspace-Token':token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.loads(response.read())
def wait_scan():
    for _ in range(200):
        report=api('report')
        if report['status']!='scanning':return report
        time.sleep(.05)
    raise RuntimeError('Scan timeout')
evidence={}
try:
    evidence['config']=api('config');evidence['config'].pop('data_location',None)
    assert subprocess.run(command,timeout=15).returncode==2;evidence['duplicate_launch']='passed'
    with urllib.request.urlopen(base_url+'/',timeout=5) as response:assert b'Clearspace' in response.read()
    api('scan',{'roots':[str(root)]});time.sleep(.1);r=wait_scan();assert r['status']=='complete';assert r['items']==1503
    evidence['synthetic_scan_items']=r['items'];evidence['scan_status']=r['status']
    page=api('entries?limit=100');ids=[e['id'] for e in page['entries'] if Path(e['path']).name.startswith('copy-')]
    assert len(ids)==2;api('duplicates',{'ids':ids,'scan_id':r['scan_id']})
    for _ in range(100):
        d=api('duplicates')
        if d['status']!='reading':break
        time.sleep(.05)
    assert len(d['groups'])==1;evidence['duplicates']='confirmed main stream only'
    api('mark',{'id':ids[0],'scan_id':r['scan_id'],'value':'keep'})
    request=urllib.request.Request(base_url+'/api/export',headers={'X-Clearspace-Token':token})
    with urllib.request.urlopen(request) as response:lines=response.read().splitlines()
    assert len(lines)==1504;evidence['export_records']=len(lines)
    api('remeasure',{});assert api('report')['after'];evidence['remeasure']='timestamped'
    api('scan',{'roots':[str(root)]});api('cancel',{});r=wait_scan();assert r['status']=='cancelled';evidence['cancellation_items']=r['items']
    api('quit',{});process.wait(timeout=20);assert process.returncode==0
    assert not (data/'session.json').exists();evidence['graceful_shutdown']='passed'
    process,base_url,token=launch();api('scan',{'roots':[str(root)]});time.sleep(.1);r=wait_scan();assert r['status']=='complete'
    assert any(e['mark']=='keep' for e in api('entries?limit=100')['entries']);evidence['restart_keep_persistence']='passed'
    api('quit',{});process.wait(timeout=20)
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=10)
evidence['data_bytes']=sum(p.stat().st_size for p in data.iterdir() if p.is_file())
Path('outputs').mkdir(exist_ok=True);Path('outputs/package-test.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence,indent=2))
