import json
import os
import threading
from unittest.mock import patch
import pytest
from clearspace.inventory import Inventory,normalize_roots
from clearspace.metadata import metadata
from clearspace.policy import validate_advice
from clearspace.duplicates import compare_selected
from clearspace.server import create_app
from fastapi.testclient import TestClient


def test_unknown_root_identity_preserved(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    original=os.stat
    class Stat:
        def __init__(self,s):self.st_dev=s.st_dev;self.st_ino=0
    with patch('clearspace.inventory.os.stat',side_effect=lambda p:Stat(original(p))):
        with patch('clearspace.inventory.os.path.isdir',return_value=True):
            assert len(normalize_roots([str(a),str(b)]))==2


def test_huge_integer_json_and_bad_model_advice(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'a').touch()
    def huge(path):
        m=metadata(path)
        if m['kind']=='file':m['logical']=2**53+71;m['allocated']=None
        return m
    inv=Inventory(tmp_path/'data',adapter=huge);inv.scan([str(root)],threading.Event())
    assert json.loads(json.dumps(inv.report()))['logical']==str(2**53+71)
    assert validate_advice('delete everything',['Review','Unknown'])=='Unknown'


def test_permission_and_disappeared_entries_are_gaps(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'locked').touch()
    def denied(path):
        if path.endswith('locked'):raise PermissionError(13,'denied')
        return metadata(path)
    inv=Inventory(tmp_path/'data',adapter=denied);inv.scan([str(root)],threading.Event())
    assert inv.report()['gaps']==1;assert inv.report()['status']=='partial'
    assert any(e['kind']=='error' for e in inv.entries()['entries'])


def test_export_holds_scan_lock_and_releases(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'a').touch()
    inv=Inventory(tmp_path/'data');inv.scan([str(root)],threading.Event())
    app=create_app(inv,'test-token','127.0.0.1:43191')
    original=inv.entries;observed=[]
    def entries(*a,**kw):
        observed.append(app.state.action_lock.locked());return original(*a,**kw)
    with patch.object(inv,'entries',side_effect=entries):
        with TestClient(app,base_url='http://127.0.0.1:43191') as c:
            r=c.get('/api/export',headers={'X-Clearspace-Token':'test-token'})
            assert r.status_code==200
    assert observed and all(observed);assert not app.state.action_lock.locked()


def test_no_shell_routes_and_oversized_payload(tmp_path):
    inv=Inventory(tmp_path/'data');app=create_app(inv,'test-token','127.0.0.1:43191')
    with TestClient(app,base_url='http://127.0.0.1:43191') as c:
        h={'X-Clearspace-Token':'test-token'}
        assert c.post('/api/scan',headers=h,content='x'*17000).status_code==413
        assert c.post('/api/delete',headers=h,json={}).status_code==404
        assert c.get('/api/entries?sort=DROP%20TABLE',headers=h).status_code==422


def test_duplicate_hardlink_is_excluded(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'a').write_bytes(b'a'*100)
    os.link(root/'a',root/'b')
    inv=Inventory(tmp_path/'data');inv.scan([str(root)],threading.Event())
    ids=[e['id'] for e in inv.entries()['entries'] if e['kind']=='file']
    result=compare_selected(inv,ids,threading.Event())
    assert result['bytes_read']=='0';assert not result['groups'];assert len(result['skipped'])==2
