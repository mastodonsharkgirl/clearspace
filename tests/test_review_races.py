import asyncio
import os
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from starlette.requests import ClientDisconnect
from clearspace.inventory import Inventory
from clearspace.duplicates import compare_selected,content_file
from clearspace.server import create_app


def pair(tmp_path):
    root=tmp_path/'selected';root.mkdir();(root/'a').write_bytes(b'x');(root/'b').write_bytes(b'x')
    inv=Inventory(tmp_path/'data');inv.scan([str(root)],threading.Event())
    ids={Path(e['path']).name:e['id'] for e in inv.entries()['entries'] if e['kind']=='file'}
    return root,inv,ids


def test_new_hardlink_is_stale(tmp_path):
    root,inv,ids=pair(tmp_path);os.link(root/'a',tmp_path/'outside-link')
    r=compare_selected(inv,[ids['a'],ids['b']],threading.Event())
    assert not r['groups']


def test_growth_cannot_exceed_content_budget(tmp_path):
    root,inv,ids=pair(tmp_path)
    @contextmanager
    def growing(path):
        if Path(path).name=='a':Path(path).write_bytes(b'x'*8192)
        with content_file(path) as f:yield f
    with patch('clearspace.duplicates.content_file',growing):r=compare_selected(inv,[ids['a'],ids['b']],threading.Event(),byte_budget=100)
    assert int(r['bytes_read'])<=100


def test_export_disconnect_before_first_yield_releases(tmp_path):
    root,inv,ids=pair(tmp_path);app=create_app(inv,'test','127.0.0.1:9999')
    endpoint=next(x.endpoint for x in app.routes if x.path=='/api/export')
    async def abort():
        response=endpoint()
        async def send(message):raise OSError('Synthetic disconnect')
        async def receive():return {'type':'http.disconnect'}
        try:await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        except ClientDisconnect:pass
        await response.body_iterator.aclose()
    asyncio.run(abort());assert not app.state.action_lock.locked()


def test_pinned_directory_prevents_junction_swap(tmp_path):
    root=tmp_path/'selected';root.mkdir();child=root/'child';child.mkdir()
    outside=tmp_path/'outside';outside.mkdir();(outside/'not-selected.txt').write_text('outside')
    inv=Inventory(tmp_path/'data');original=os.scandir;attempts=[]
    def swap(path):
        if Path(path)==child and not attempts:
            attempts.append(True)
            child.rename(root/'original-child')
            result=subprocess.run(['cmd','/c','mklink','/J',str(child),str(outside)],capture_output=True)
            assert result.returncode==0
        return original(path)
    try:
        with patch('clearspace.inventory.os.scandir',swap):inv.scan([str(root)],threading.Event())
        assert 'not-selected.txt' not in [Path(e['path']).name for e in inv.entries()['entries']]
        assert inv.report()['status']=='partial'
    finally:
        if child.is_junction():os.rmdir(child)
