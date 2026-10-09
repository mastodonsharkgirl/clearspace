import os
import threading
from pathlib import Path

from clearspace.inventory import Inventory, normalize_roots
from clearspace.metadata import metadata


def test_overlap(tmp_path):
    root = tmp_path / 'fixture'; root.mkdir(); sub = root / 'nested'; sub.mkdir()
    assert normalize_roots([str(sub), str(root), str(root)]) == [str(root)]


def test_metadata_does_not_read_contents(tmp_path, monkeypatch):
    f = tmp_path / '秘密.txt'; f.write_bytes(b'x' * 12000)
    import builtins
    monkeypatch.setattr(builtins, 'open', lambda *a, **k: (_ for _ in ()).throw(AssertionError('content read')))
    m = metadata(str(f))
    assert m['logical'] == 12000
    assert m['allocated'] is not None


def test_scan_hardlinks_and_pagination(tmp_path):
    root = tmp_path / 'fixture'; root.mkdir()
    f = root / 'one.bin'; f.write_bytes(b'a' * 12000)
    os.link(f, root / 'two.bin')
    inv = Inventory(tmp_path / 'data')
    inv.scan([str(root)], threading.Event())
    r = inv.report()
    assert r['status'] == 'complete'
    assert r['items'] == 3
    assert int(r['logical']) == 24000
    assert int(r['allocated']) == metadata(str(f))['allocated']
    assert int(r['reviewable']) == 0
    assert len(inv.entries(limit=1)['entries']) == 1


def test_cancel_and_budget(tmp_path):
    root = tmp_path / 'fixture'; root.mkdir()
    for n in range(20): (root / str(n)).write_text('a')
    inv = Inventory(tmp_path / 'data', max_items=5)
    inv.scan([str(root)], threading.Event())
    assert inv.report()['status'] == 'partial'
    assert inv.report()['items'] <= 5
    event = threading.Event(); event.set()
    inv.scan([str(root)], event)
    assert inv.report()['status'] == 'cancelled'


def test_unknown_allocation_never_zero(tmp_path):
    root = tmp_path / 'fixture'; root.mkdir(); (root / 'a').write_text('a')
    def adapter(path):
        m = metadata(path); m['allocated'] = None; m['allocation_status'] = 'unsupported'; return m
    inv = Inventory(tmp_path / 'data', adapter=adapter)
    inv.scan([str(root)], threading.Event())
    assert inv.report()['unknown_allocation'] == 1
    assert inv.entries()['entries'][1]['allocated'] is None


def test_ordinary_ntfs_allocation_is_not_file_length(tmp_path):
    f=tmp_path/'ordinary.bin'; f.write_bytes(b'x'*5001)
    m=metadata(str(f))
    assert m['logical']==5001
    assert m['allocated']>=8192
    assert m['allocated']%4096==0


def test_connections_close(tmp_path):
    inv=Inventory(tmp_path/'data')
    with inv.connect() as c: c.execute('SELECT 1')
    import sqlite3,pytest
    with pytest.raises(sqlite3.ProgrammingError): c.execute('SELECT 1')
