"""Own one explicitly loopback socket; never log bootstrap credentials."""
import socket
import threading
import webbrowser
from pathlib import Path


def launch(*, roots=(), port=0, host='127.0.0.1', browser=True):
    if host!='127.0.0.1':raise ValueError('Studio binds only to 127.0.0.1')
    import uvicorn
    from .security import Config
    from .app import create_app
    roots=tuple(roots) or (Path.cwd()/'projects',)
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.bind((host,port));sock.listen(128)
        config=Config(roots=roots,port=sock.getsockname()[1]);app=create_app(config)
        if not (config.static/'index.html').is_file():raise ValueError('Studio frontend is not built. See docs/studio_development.md')
        server=uvicorn.Server(uvicorn.Config(app,host=host,port=config.port,access_log=False,log_level='warning',proxy_headers=False,limit_concurrency=16))
        if browser:
            def open_browser():
                import time
                while not server.started and not server.should_exit:time.sleep(.05)
                if server.started:webbrowser.open(config.origin+'/#bootstrap='+config.bootstrap)
            threading.Thread(target=open_browser,daemon=True).start()
        print('VehicleRecon Studio: '+config.origin+' (Ctrl+C to stop)',flush=True)
        server.run(sockets=[sock])
    finally:sock.close()
