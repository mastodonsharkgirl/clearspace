# PyInstaller 6.22.3, Windows x64 / Python 3.13.
a = Analysis(['run_clearspace.py'], pathex=[], binaries=[], datas=[('dist','frontend'),('clearspace/build_info.json','clearspace')], hiddenimports=['uvicorn.logging','uvicorn.loops.auto','uvicorn.protocols.http.h11_impl','uvicorn.lifespan.on'], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['pytest','httpx','httpx2'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='Clearspace',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,disable_windowed_traceback=True)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Clearspace')
