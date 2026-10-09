"""Metadata only. No file content handles are opened here."""
import ctypes
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

REPARSE = 0x400
CLOUD = 0x1000 | 0x40000 | 0x400000


def now():
    return datetime.now(timezone.utc).isoformat()


def native(path):
    path = os.path.abspath(path)
    return '\\\\?\\' + path if os.name == 'nt' and not path.startswith('\\\\') else path


def safe_local(path):
    p = Path(os.path.abspath(path))
    if str(p).startswith('\\\\'):
        raise ValueError('Network and device paths are not supported')
    for part in [p, *p.parents]:
        s = os.lstat(part)
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & REPARSE:
            raise ValueError('Reparse roots or ancestors are excluded')
    if os.name == 'nt':
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        if k.GetDriveTypeW(p.anchor) != 3:
            raise ValueError('Select an ordinary fixed local volume')
    return str(p)


def filesystem(path):
    if os.name != 'nt': return 'unsupported'
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    root = ctypes.create_unicode_buffer(32768)
    if not k.GetVolumePathNameW(ctypes.c_wchar_p(native(path)), root, len(root)): return 'unknown'
    name = ctypes.create_unicode_buffer(256)
    if not k.GetVolumeInformationW(root, None, 0, None, None, None, name, len(name)): return 'unknown'
    return name.value


def metadata(path):
    s = os.lstat(native(path))
    attrs = getattr(s, 'st_file_attributes', 0)
    reparse = bool(attrs & REPARSE or stat.S_ISLNK(s.st_mode))
    cloud = 'possible-placeholder' if attrs & CLOUD else ('unknown-reparse' if reparse else 'ordinary-local')
    kind = 'directory' if stat.S_ISDIR(s.st_mode) else ('file' if stat.S_ISREG(s.st_mode) else 'other')
    allocated = None
    status = 'excluded' if reparse or cloud != 'ordinary-local' else 'unknown'
    if kind == 'file' and not reparse and cloud == 'ordinary-local':
        if os.name == 'nt' and filesystem(path) == 'NTFS' and attrs & (0x800 | 0x200):
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.GetCompressedFileSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
            k.GetCompressedFileSizeW.restype = ctypes.c_ulong
            high = ctypes.c_ulong()
            ctypes.set_last_error(0)
            low = k.GetCompressedFileSizeW(native(path), ctypes.byref(high))
            err = ctypes.get_last_error()
            if low != 0xffffffff or err == 0:
                allocated = (high.value << 32) | low; status = 'known-default-stream'
            else: status = f'error-{err}'
        elif os.name == 'nt' and filesystem(path) == 'NTFS':
            k=ctypes.WinDLL('kernel32',use_last_error=True)
            k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
            k.CreateFileW.restype=ctypes.c_void_p
            h=k.CreateFileW(native(path),0,7,None,3,0x00200000,None)
            if h != ctypes.c_void_p(-1).value:
                class Standard(ctypes.Structure):
                    _fields_=[('allocation',ctypes.c_longlong),('length',ctypes.c_longlong),('links',ctypes.c_ulong),('deleted',ctypes.c_ubyte),('directory',ctypes.c_ubyte)]
                info=Standard()
                try:
                    if k.GetFileInformationByHandleEx(ctypes.c_void_p(h),1,ctypes.byref(info),ctypes.sizeof(info)):
                        allocated=info.allocation; status='known-default-stream'
                finally: k.CloseHandle(ctypes.c_void_p(h))
            else: status=f'error-{ctypes.get_last_error()}'
        else: status = 'unsupported-filesystem'
        after=os.lstat(native(path))
        if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,attrs)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,getattr(after,'st_file_attributes',0)):
            allocated=None; status='stale-during-measurement'
    identity = f'{s.st_dev}:{s.st_ino}' if s.st_ino else None
    return dict(path=path, parent=str(Path(path).parent), kind=kind, logical=s.st_size if kind == 'file' else 0,
                allocated=allocated, allocation_status=status, identity=identity, volume=str(s.st_dev),
                modified_ns=str(s.st_mtime_ns), links=s.st_nlink, attributes=attrs,
                reparse=reparse, reparse_tag=getattr(s, 'st_reparse_tag', 0), cloud=cloud, error=None)


def volume_space(path):
    if os.name != 'nt':
        import shutil
        d = shutil.disk_usage(path)
        return dict(at=now(), volume=str(os.stat(path).st_dev), available=str(d.free), free=str(d.free), total=str(d.total))
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    values = [ctypes.c_ulonglong() for _ in range(3)]
    if not k.GetDiskFreeSpaceExW(ctypes.c_wchar_p(native(path)), *[ctypes.byref(x) for x in values]):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(at=now(), volume=str(os.stat(path).st_dev), available=str(values[0].value), total=str(values[1].value), free=str(values[2].value))
