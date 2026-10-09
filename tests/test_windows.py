import ctypes
import os
import subprocess
import threading
from pathlib import Path
import pytest
from clearspace.metadata import metadata
from clearspace.inventory import Inventory

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Physical Windows test')


def test_sparse_over_4gib(tmp_path):
    p=tmp_path/'sparse.bin';p.touch()
    result=subprocess.run(['fsutil','sparse','setflag',str(p)],capture_output=True)
    assert result.returncode==0
    # CRT truncate can zero-fill; native SetFilePointerEx/SetEndOfFile preserves holes.
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.restype=ctypes.c_void_p
    h=k.CreateFileW(ctypes.c_wchar_p(str(p)),0x40000000,0,None,3,0,None)
    assert h!=ctypes.c_void_p(-1).value
    try:
        assert k.SetFilePointerEx(ctypes.c_void_p(h),ctypes.c_longlong(5*1024**3+17),None,0)
        assert k.SetEndOfFile(ctypes.c_void_p(h))
    finally:k.CloseHandle(ctypes.c_void_p(h))
    m=metadata(str(p));assert m['logical']==5*1024**3+17;assert m['allocated']==0
    inv=Inventory(tmp_path/'data');inv.scan([str(tmp_path)],threading.Event())
    assert inv.report()['logical']==str(5*1024**3+17)


def test_compressed_allocation(tmp_path):
    p=tmp_path/'compress.bin';p.write_bytes(b'A'*1024*1024)
    r=subprocess.run(['compact','/C',str(p)],capture_output=True)
    assert r.returncode==0
    m=metadata(str(p));assert m['attributes'] & 0x800
    assert m['allocated']<m['logical']


def test_unicode_long_path(tmp_path):
    root=tmp_path/'fixture';p=root
    for i in range(7):p=p/('長い名前'+str(i)+'x'*35)
    p.mkdir(parents=True);f=p/'résumé.txt';f.write_text('hello')
    inv=Inventory(tmp_path/'data');inv.scan([str(root)],threading.Event())
    assert inv.report()['status']=='complete'
    assert inv.report()['logical']=='5'


def test_junction_cycle_excluded(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'a').write_text('data')
    # Creating a junction is confined to this disposable fixture. No deletion/move shell operations.
    r=subprocess.run(['cmd','/c','mklink','/J',str(root/'cycle'),str(root)],capture_output=True)
    assert r.returncode==0
    try:
        inv=Inventory(tmp_path/'data');inv.scan([str(root)],threading.Event())
        assert inv.report()['status']=='partial';assert inv.report()['items']==3
    finally: os.rmdir(root/'cycle')


def test_low_storage_and_cloud_logic(tmp_path):
    root=tmp_path/'fixture';root.mkdir();(root/'a').write_text('data')
    inv=Inventory(tmp_path/'data',reserve=2**63)
    inv.scan([str(root)],threading.Event());assert inv.report()['status']=='partial'
    assert inv.report()['items']==0
    def cloud(path):
        m=metadata(path)
        if m['kind']=='file':m.update(cloud='possible-placeholder',reparse=True,allocated=None,allocation_status='excluded')
        return m
    inv=Inventory(tmp_path/'cloud-data',adapter=cloud);inv.scan([str(root)],threading.Event())
    assert inv.report()['unknown_allocation']==1;assert inv.report()['status']=='partial'
