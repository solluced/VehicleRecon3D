"""Trusted E2E harness: credentials arrive on stdin, never in logs or argv."""
import json
import socket
import sys
import os
from pathlib import Path
import uvicorn
from vehiclerecon_studio.app import create_app
from vehiclerecon_studio.security import Config

if __name__=='__main__':
    options=json.loads(sys.stdin.readline())
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    config=Config((Path(options['root']),),sock.getsockname()[1],bootstrap=options['secret'],cv_enabled=options.get('cv_enabled',True))
    server=uvicorn.Server(uvicorn.Config(create_app(config),access_log=False,log_level='error',proxy_headers=False))
    print(json.dumps({'origin':config.origin,'pid':os.getpid()}),flush=True)
    try:server.run(sockets=[sock])
    finally:sock.close()
