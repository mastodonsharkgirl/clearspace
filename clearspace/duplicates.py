import ctypes
import hashlib
import os
from contextlib import contextmanager
from .metadata import metadata, safe_local, native, REPARSE, CLOUD


def signature(m):
    return tuple(m[k] for k in ('identity','logical','modified_ns','cloud','reparse','links'))


def validate_open_file(f,m):
    s=os.fstat(f.fileno())
    if s.st_size!=m['logical'] or s.st_mtime_ns!=int(m['modified_ns']) or s.st_nlink!=1 or f'{s.st_dev}:{s.st_ino}'!=m['identity']:
        raise ValueError('File identity, size or links changed before content read')


@contextmanager
def content_file(path):
    safe_local(path)
    if os.name == 'nt':
        import msvcrt
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
        k.CreateFileW.restype=ctypes.c_void_p
        h=k.CreateFileW(native(path),0x80000000,1,None,3,0x00200000|0x08000000,None)
        if h == ctypes.c_void_p(-1).value: raise OSError('File cannot be read exclusively against writes')
        k.CloseHandle.argtypes=[ctypes.c_void_p]
        try:
            class Info(ctypes.Structure):
                _fields_=[('attrs',ctypes.c_ulong),('rest',ctypes.c_ulong*12)]
            info=Info()
            if not k.GetFileInformationByHandle(ctypes.c_void_p(h),ctypes.byref(info)) or info.attrs & (REPARSE|CLOUD): raise OSError('Reparse/cloud content excluded')
            final=ctypes.create_unicode_buffer(32768)
            if not k.GetFinalPathNameByHandleW(ctypes.c_void_p(h),final,len(final),0): raise OSError('Cannot validate final path')
            if final.value.casefold()!=native(path).casefold(): raise OSError('Path changed during open')
            fd=msvcrt.open_osfhandle(h,os.O_RDONLY|os.O_BINARY); h=None
        finally:
            if h is not None: k.CloseHandle(h)
        with os.fdopen(fd,'rb') as f: yield f
    else:
        with open(path,'rb') as f: yield f


def compare_selected(inv, ids, cancel, byte_budget=2*1024**3):
    if not 2 <= len(ids) <= 100 or len(set(ids)) != len(ids): raise ValueError('Select 2 to 100 distinct files')
    groups={}; skipped=[]; used=0
    for id in ids:
        if cancel.is_set(): break
        m=inv.entry(id)
        try:
            if m['kind']!='file' or m['cloud']!='ordinary-local' or m['reparse'] or not m['identity'] or m['links'] != 1: raise ValueError('Ineligible cloud, reparse, shared-link or unidentified item')
            before=metadata(m['path'])
            if signature(before)!=signature(m): raise ValueError('Stale since scan')
            if used+m['logical']*3 > byte_budget: raise ValueError('Content-read budget reached; select smaller groups')
            digest=hashlib.sha256()
            with content_file(m['path']) as f:
                validate_open_file(f,m)
                remaining=m['logical']
                while remaining:
                    if cancel.is_set(): raise ValueError('Cancelled')
                    amount=min(1024*1024,remaining,byte_budget-used)
                    if amount<=0:raise ValueError('Content-read budget reached')
                    chunk=f.read(amount)
                    if not chunk:raise ValueError('File shrank during hashing')
                    used+=len(chunk); digest.update(chunk)
                    remaining-=len(chunk)
                validate_open_file(f,m)
            if signature(metadata(m['path']))!=signature(before): raise ValueError('Changed during hashing')
            groups.setdefault((m['logical'],digest.hexdigest()),[]).append((id,m))
        except (OSError,ValueError) as e: skipped.append(dict(id=id,reason=str(e)))
    confirmed=[]
    for (_,digest), candidates in groups.items():
        if len(candidates)<2: continue
        first_id,first=candidates[0]; equal=[first_id]
        for id,m in candidates[1:]:
            try:
                if cancel.is_set(): raise ValueError('Cancelled')
                if signature(metadata(first['path']))!=signature(first) or signature(metadata(m['path']))!=signature(m): raise ValueError('Stale before comparison')
                same=True
                with content_file(first['path']) as a, content_file(m['path']) as b:
                    validate_open_file(a,first);validate_open_file(b,m)
                    remaining=m['logical']
                    while remaining:
                        if cancel.is_set(): raise ValueError('Cancelled')
                        amount=min(1024*1024,remaining,(byte_budget-used)//2)
                        if amount<=0:raise ValueError('Content-read budget reached')
                        x,y=a.read(amount),b.read(amount); used+=len(x)+len(y)
                        if x!=y: same=False; break
                        if not x:raise ValueError('File shrank during comparison')
                        remaining-=len(x)
                    validate_open_file(a,first);validate_open_file(b,m)
                if signature(metadata(first['path']))!=signature(first) or signature(metadata(m['path']))!=signature(m): raise ValueError('Changed during comparison')
                if same: equal.append(id)
            except (OSError,ValueError) as e: skipped.append(dict(id=id,reason=str(e)))
        if len(equal)>1: confirmed.append(dict(ids=equal,sha256=digest,label='Identical main file contents',keeper=None))
    return dict(groups=confirmed,skipped=skipped,bytes_read=str(used),stream_coverage='default-only',status='cancelled' if cancel.is_set() else 'complete',notice='Named streams excluded. Equal contents do not establish dispensability. Results describe the comparison time; rescan after changes.')
