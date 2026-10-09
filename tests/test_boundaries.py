import os
import threading
import time
from clearspace.inventory import Inventory
from clearspace.duplicates import compare_selected
from clearspace.server import create_app
from fastapi.testclient import TestClient


def fixture(tmp_path):
    root=tmp_path/'Downloads'; root.mkdir()
    for name,data in [('a.bin',b'aaa'),('b.bin',b'aaa'),('c.bin',b'bbb')]: (root/name).write_bytes(data)
    inv=Inventory(tmp_path/'data'); inv.scan([str(root)],threading.Event())
    ids={os.path.basename(x['path']):x['id'] for x in inv.entries()['entries']}
    return root,inv,ids


def test_duplicates_require_content_equality(tmp_path):
    root,inv,ids=fixture(tmp_path)
    result=compare_selected(inv,[ids['a.bin'],ids['b.bin'],ids['c.bin']],threading.Event())
    assert result['groups'][0]['ids']==[ids['a.bin'],ids['b.bin']]
    assert result['groups'][0]['label']=='Identical main file contents'
    assert result['stream_coverage']=='default-only'


def test_changed_since_scan_is_stale(tmp_path):
    root,inv,ids=fixture(tmp_path); (root/'a.bin').write_bytes(b'different')
    result=compare_selected(inv,[ids['a.bin'],ids['b.bin']],threading.Event())
    assert not result['groups']
    assert result['skipped']


def test_unique_sizes_are_not_read(tmp_path):
    root,inv,ids=fixture(tmp_path)
    (root/'a.bin').write_bytes(b'a');(root/'b.bin').write_bytes(b'bb')
    inv.scan([str(root)],threading.Event())
    selected=[e['id'] for e in inv.entries()['entries'] if e['kind']=='file']
    result=compare_selected(inv,selected,threading.Event())
    assert result['bytes_read']=='0'


def test_security_gate_and_bounded_ids(tmp_path):
    root,inv,ids=fixture(tmp_path)
    app=create_app(inv,'test-token','127.0.0.1:43191')
    with TestClient(app,base_url='http://127.0.0.1:43191') as c:
        assert c.get('/api/report').status_code==403
        assert c.get('/api/report',headers={'X-Clearspace-Token':'test-token','Origin':'https://evil.test'}).status_code==403
        assert c.get('/api/report',headers={'X-Clearspace-Token':'test-token','Host':'evil.test'}).status_code==403
        h={'X-Clearspace-Token':'test-token'}
        assert c.get('/api/report',headers=h).status_code==200
        assert c.post('/api/open',headers=h,json={'id':99999,'scan_id':inv.state()['scan_id']}).status_code==400
        assert c.post('/api/settings',headers=h,json={'action':'cmd.exe'}).status_code==422
        assert c.post('/api/mark',headers=h,json={'id':ids['a.bin'],'scan_id':'old','value':'keep'}).status_code==409
        assert c.post('/api/mark',headers=h,json={'id':ids['a.bin'],'scan_id':inv.state()['scan_id'],'value':'keep'}).status_code==200
