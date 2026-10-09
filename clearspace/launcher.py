"""Portable launcher. No service, startup entry or elevated operation."""
import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
import uvicorn
from .inventory import Inventory
from .server import create_app


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'Clearspace')
    parser.add_argument('--headless',action='store_true',help='Developer/package test mode; no automatic browser')
    parser.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    args.data.mkdir(parents=True,exist_ok=True)
    # A per-data-directory lock has no secrets and is released by Windows on crash.
    import msvcrt
    lock=open(args.data/'session.lock','a+b')
    if lock.tell()==0:lock.write(b'0');lock.flush()
    lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        if not args.headless:
            import tkinter.messagebox
            tkinter.messagebox.showinfo('Clearspace is already running','Use Open Clearspace in the existing launcher. Quit that launcher before starting another session.')
        return 2
    root=None;pick_requests=[]
    if not args.headless:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.title('Clearspace · local preview');root.geometry('440x265');root.resizable(False,False)
        root.configure(bg='#f4f3ed')
        tk.Label(root,text='clearspace',font=('Segoe UI',24),bg='#f4f3ed',fg='#344f38').pack(pady=(20,8))
        tk.Label(root,text='Local, read-only disk planner · unsigned preview\nClosing the browser does not stop the app.',bg='#f4f3ed',font=('Segoe UI',10)).pack()

    sock=socket.socket();sock.bind(('127.0.0.1',args.port));port=sock.getsockname()[1]
    token=secrets.token_urlsafe(32);host=f'127.0.0.1:{port}';url=f'http://{host}/#token={token}'
    inv=Inventory(args.data)
    if inv.state()['status']=='scanning':inv.fail()
    frontend=(Path(sys._MEIPASS)/'frontend') if getattr(sys,'frozen',False) else Path(__file__).parent.parent/'dist'
    def pick():
        event=threading.Event();result=[];pick_requests.append((event,result));event.wait(120)
        return result[0] if result else ''
    quit_event=threading.Event()
    app=create_app(inv,token,host,frontend,pick_folder=pick if root else None,shutdown=quit_event.set)
    config=uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False,log_config=None)
    server=uvicorn.Server(config)
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=False);thread.start()
    session=args.data/'session.json'
    session.write_text(json.dumps({'url':url,'port':port,'pid':os.getpid()}))
    def stop():
        app.state.cancel.set()
        if app.state.worker:app.state.worker.join(timeout=15)
        server.should_exit=True;thread.join(timeout=15)
        sock.close()
        if session.exists():session.unlink()
        lock.close()
        if root:root.destroy()
    if root:
        import tkinter as tk
        from tkinter import filedialog
        tk.Button(root,text='Open Clearspace',command=lambda:webbrowser.open(url),font=('Segoe UI',11),bg='#344f38',fg='white',width=24).pack(pady=(15,8))
        def change_data():
            folder=filedialog.askdirectory(title='Choose a dedicated Clearspace data folder')
            if folder:
                stop()
                command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).parent.parent/'run_clearspace.py')]
                subprocess.Popen(command+['--data',str(Path(folder)/'Clearspace-data')],shell=False)
        tk.Button(root,text='Choose data location…',command=change_data,width=24).pack(pady=3)
        tk.Button(root,text='Quit Clearspace',command=stop,width=24).pack(pady=5)
        root.protocol('WM_DELETE_WINDOW',stop)
        opened=False
        def tick():
            nonlocal opened
            if quit_event.is_set():stop();return
            if not opened and server.started:
                try:
                    with urllib.request.urlopen(f'http://{host}/health',timeout=1) as response:
                        if response.status==200:webbrowser.open(url);opened=True
                except OSError:pass
            if pick_requests:
                event,result=pick_requests.pop(0)
                result.append(filedialog.askdirectory(title='Choose a folder to scan (metadata only)'));event.set()
            root.after(100,tick)
        root.after(100,tick);root.mainloop()
    else:
        try:
            while thread.is_alive() and not quit_event.is_set():time.sleep(.2)
        except KeyboardInterrupt:pass
        finally:stop()
    return 0


if __name__=='__main__':sys.exit(main())
