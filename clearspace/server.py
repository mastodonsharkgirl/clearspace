import json
import os
import secrets
import subprocess
import threading
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import __version__
from .inventory import normalize_roots
from .metadata import safe_local, metadata
from .duplicates import compare_selected, signature


class Scope(BaseModel):
    roots: list[str] = Field(min_length=1,max_length=8)
    protected: list[str] = Field(default_factory=list,max_length=32)

class Item(BaseModel):
    id: int = Field(ge=1)
    scan_id: str = Field(max_length=64)

class Mark(Item):
    value: Literal['keep','later','review']

class Selection(BaseModel):
    ids: list[int] = Field(min_length=2,max_length=100)
    scan_id: str = Field(max_length=64)

class Settings(BaseModel):
    action: Literal['storage','apps']


def create_app(inv, token, host, frontend=None, pick_folder=None, shutdown=None):
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    app.state.cancel=threading.Event(); app.state.worker=None; app.state.duplicates=None
    app.state.action_lock=threading.Lock()

    @app.middleware('http')
    async def guard(request:Request, call_next):
        if request.headers.get('host') != host: return JSONResponse({'detail':'Host refused'},403)
        origin=request.headers.get('origin')
        if origin and origin!=f'http://{host}': return JSONResponse({'detail':'Origin refused'},403)
        if request.headers.get('sec-fetch-site')=='cross-site': return JSONResponse({'detail':'Cross-site request refused'},403)
        if request.url.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('x-clearspace-token',''),token): return JSONResponse({'detail':'Open this session from the launcher'},403)
        if request.method not in {'GET','HEAD'}:
            length=request.headers.get('content-length')
            if not length or not length.isdigit() or int(length)>16384: return JSONResponse({'detail':'Request too large or missing length'},413)
        response=await call_next(request)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"})
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request,exc): return JSONResponse({'detail':str(exc)},400)
    @app.exception_handler(OSError)
    async def bad_os(request,exc): return JSONResponse({'detail':'Windows could not complete this operation. The item may have moved or access is restricted.'},400)

    def idle():
        if app.state.worker and app.state.worker.is_alive(): raise HTTPException(409,'Wait for the active operation or cancel it')
    def current(scan_id):
        idle()
        if inv.state().get('scan_id')!=scan_id: raise HTTPException(409,'Inventory changed; refresh and select again')
    def work(fn):
        idle(); app.state.cancel.clear()
        app.state.worker=threading.Thread(target=fn,daemon=False); app.state.worker.start()

    @app.get('/health')
    def health(): return {'app':'Clearspace','version':__version__}
    @app.get('/api/config')
    def config():
        build=Path(__file__).parent/'build_info.json'
        return dict(inv.preflight(),version=__version__,signing='unsigned',build=json.loads(build.read_text()) if build.exists() else {'source_commit':'development'},picker=pick_folder is not None)
    @app.post('/api/quit')
    def quit_app():
        if shutdown is None: raise HTTPException(409,'Quit from the launcher')
        app.state.cancel.set();shutdown();return {'quitting':True}
    @app.post('/api/pick')
    def pick():
        if pick_folder is None: raise HTTPException(409,'Enter a local folder path')
        return {'path':pick_folder()}
    @app.get('/api/report')
    def report(): return inv.report()
    @app.get('/api/entries')
    def entries(offset:int=Query(0,ge=0,le=500000),limit:int=Query(50,ge=1,le=100),sort:Literal['allocated','logical','path']='allocated',direction:Literal['asc','desc']='desc',category:str|None=Query(None,max_length=100)):
        return inv.entries(offset,limit,sort,direction,category)
    @app.post('/api/scan')
    def scan(scope:Scope):
        with app.state.action_lock:
            idle(); roots=normalize_roots(scope.roots)
            protected=[safe_local(p) for p in scope.protected]
            app.state.duplicates=None
            def run_scan():
                try: inv.scan(scope.roots,app.state.cancel,protected)
                except Exception: inv.fail()
            work(run_scan)
        return {'started':True}
    @app.post('/api/cancel')
    def cancel(): app.state.cancel.set(); return {'requested':True}
    @app.post('/api/mark')
    def mark(item:Mark):
        with app.state.action_lock: current(item.scan_id); inv.mark(item.id,item.value)
        return {'saved':True}
    @app.post('/api/open')
    def open_folder(item:Item):
        with app.state.action_lock:
            current(item.scan_id); m=inv.entry(item.id)
            safe_local(m['path'])
            if signature(metadata(m['path']))!=signature(m): raise ValueError('Item changed since scan; rescan first')
            parent=safe_local(m['parent'])
            roots=inv.state()['roots']
            if not any(Path(parent)==Path(r) or Path(r) in Path(parent).parents for r in roots): raise ValueError('Folder is outside selected scope')
            subprocess.Popen([str(Path(os.environ['WINDIR'])/'explorer.exe'),parent],shell=False)
        return {'opened':True}
    @app.post('/api/settings')
    def settings(body:Settings):
        os.startfile({'storage':'ms-settings:storagesense','apps':'ms-settings:appsfeatures'}[body.action])
        return {'opened':True}
    @app.post('/api/remeasure')
    def remeasure():
        with app.state.action_lock: idle(); return inv.remeasure()
    @app.post('/api/duplicates')
    def duplicates(selection:Selection):
        with app.state.action_lock:
            current(selection.scan_id)
            for id in selection.ids: inv.entry(id)
            app.state.duplicates={'status':'reading','groups':[],'skipped':[]}
            def run():
                try: app.state.duplicates=compare_selected(inv,selection.ids,app.state.cancel)
                except (ValueError,OSError): app.state.duplicates={'status':'failed','groups':[],'skipped':[]}
            work(run)
        return {'started':True}
    @app.get('/api/duplicates')
    def duplicate_status(): return app.state.duplicates
    @app.get('/api/export')
    def export():
        if not app.state.action_lock.acquire(blocking=False): raise HTTPException(409,'Another action is active')
        try: idle()
        except Exception:
            app.state.action_lock.release(); raise
        def generate():
            try:
                yield json.dumps({'report':inv.report(),'notice':'Private local paths. Review before sharing.'})+'\n'
                offset=0
                while True:
                    page=inv.entries(offset,100)
                    for e in page['entries']: yield json.dumps(e)+'\n'
                    offset+=100
                    if offset>=page['total']: break
            finally: app.state.action_lock.release()
        return StreamingResponse(generate(),media_type='application/x-ndjson',headers={'Content-Disposition':'attachment; filename="Clearspace-plan.ndjson"'})
    if frontend: app.mount('/',StaticFiles(directory=frontend,html=True),name='ui')
    return app
