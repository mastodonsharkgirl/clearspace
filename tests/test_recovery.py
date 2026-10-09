import threading
import pytest
from clearspace.inventory import Inventory


def test_picker_single_request_cancel_and_retry():
    from clearspace.picker import FolderPicker
    calls=[]
    picker=FolderPicker(lambda: calls.append(1) or '')
    first=picker.request()
    assert first['status']=='pending'
    assert picker.request()==first
    picker.run_pending()
    assert picker.state()['status']=='cancelled'
    assert calls==[1]
    picker.request(); picker.run_pending()
    assert calls==[1,1]


def test_picker_error_can_retry():
    from clearspace.picker import FolderPicker
    def fail(): raise RuntimeError('private internal details')
    picker=FolderPicker(fail)
    picker.request(); picker.run_pending()
    assert picker.state()['status']=='error'
    assert 'private' not in str(picker.state())
    assert picker.request()['status']=='pending'


def test_drive_letter_means_root_not_current_directory(monkeypatch):
    import clearspace.inventory as module
    captured=[]
    def canonical(path): captured.append(path); raise ValueError('test boundary')
    monkeypatch.setattr(module,'canonical_root',canonical)
    with pytest.raises(ValueError): module.normalize_roots(['C:'])
    assert captured==['C:\\']


@pytest.mark.parametrize('path',['','   ','Downloads','C:Downloads'])
def test_ambiguous_relative_scopes_are_rejected(path):
    from clearspace.inventory import normalize_roots
    with pytest.raises(ValueError,match='full folder path'):
        normalize_roots([path])


def test_folder_rollup_and_navigation(tmp_path):
    root=tmp_path/'fixture'; root.mkdir()
    large=root/'Large'; large.mkdir(); nested=large/'Nested'; nested.mkdir()
    (nested/'big.bin').write_bytes(b'x'*65536)
    (root/'small.txt').write_text('small')
    inv=Inventory(tmp_path/'data'); inv.scan([str(root)],threading.Event())
    overview=inv.browse()
    assert overview['entries'][0]['path']==str(root)
    rows=inv.browse(str(root))['entries']
    assert rows[0]['path']==str(large)
    assert int(rows[0]['allocated'])>=65536
    assert rows[0]['files']==1
    assert inv.browse(str(large))['entries'][0]['path']==str(nested)
    assert inv.browse(str(nested))['entries'][0]['path']==str(nested/'big.bin')
    with pytest.raises(ValueError): inv.browse(str(tmp_path))


def test_picker_http_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from clearspace.server import create_app
    from clearspace.picker import FolderPicker
    picker=FolderPicker(lambda: str(tmp_path))
    inv=Inventory(tmp_path/'data')
    with TestClient(create_app(inv,'test','testserver',pick_folder=picker)) as client:
        headers={'X-Clearspace-Token':'test'}
        first=client.post('/api/pick',json={},headers=headers).json()
        assert first['status']=='pending'
        assert client.post('/api/pick',json={},headers=headers).json()==first
        picker.run_pending()
        assert client.get('/api/pick',headers=headers).json()['status']=='selected'
        assert client.get('/api/pick').status_code==403


def test_rollups_are_bounded_and_deduplicate_link_names(tmp_path):
    import os
    root=tmp_path/'fixture'; root.mkdir()
    data=root/'file.bin'; data.write_bytes(b'x'*65536); os.link(data,root/'alias.bin')
    for i in range(55): (root/f'dir-{i:02}').mkdir()
    inv=Inventory(tmp_path/'data'); inv.scan([str(root)],threading.Event())
    assert inv.browse()['entries'][0]['allocated']==inv.report()['allocated']
    first=inv.browse(str(root)); second=inv.browse(str(root),offset=50)
    assert len(first['entries'])==50 and first['has_more']
    assert len(second['entries'])==7 and not second['has_more']


def test_folder_file_opens_existing_review_details(tmp_path):
    from fastapi.testclient import TestClient
    from clearspace.server import create_app
    root=tmp_path/'fixture'; root.mkdir(); (root/'review.txt').write_text('fixture')
    inv=Inventory(tmp_path/'data'); inv.scan([str(root)],threading.Event())
    file=inv.browse(str(root))['entries'][0]
    inv.mark(file['id'],'keep')
    with TestClient(create_app(inv,'test','testserver')) as client:
        result=client.get(f"/api/entry/{file['id']}",headers={'X-Clearspace-Token':'test'})
        assert result.status_code==200
        assert result.json()['mark']=='keep'
        assert result.json()['id']==file['id']
        assert result.json()['path']==str(root/'review.txt')


def test_unknown_file_allocation_stays_unknown_in_browse(tmp_path):
    from clearspace.metadata import metadata
    root=tmp_path/'fixture'; root.mkdir(); (root/'unknown.bin').write_bytes(b'fixture')
    def adapter(path):
        item=metadata(path)
        if item['kind']=='file': item.update(allocated=None,allocation_status='unsupported')
        return item
    inv=Inventory(tmp_path/'data',adapter=adapter); inv.scan([str(root)],threading.Event())
    leaf=inv.browse(str(root))['entries'][0]
    assert leaf['allocated'] is None
    assert leaf['unknown']==1
    assert inv.browse()['entries'][0]['allocated']=='0'


def test_access_error_gets_local_coverage_guidance(tmp_path):
    inv=Inventory(tmp_path/'data')
    state=inv.state()
    with inv.connect() as c:
        inv.record_error(c,state,str(tmp_path/'unavailable'),'coverage-5')
        inv.save_state(c,state)
    item=inv.entries()['entries'][0]
    assert item['guidance']=='coverage'
    assert item['category']=='Protected / unknown'
    assert 'not be measured' in item['reason']
