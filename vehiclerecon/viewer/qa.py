"""Isolated local Chromium regression. Never attach to the user's browser."""
import os,shutil,socket,subprocess
from pathlib import Path
from ..core.errors import BlockedError,GateError
from ..core.project import read_json
from ..core.manifest import digest_file

def browser():
    candidates=[os.environ.get('VEHICLERECON_BROWSER'),shutil.which('chromium'),shutil.which('google-chrome')]
    for base in (os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'),os.environ.get('ProgramFiles','C:/Program Files')):
        candidates += [str(Path(base)/'Microsoft/Edge/Application/msedge.exe'),str(Path(base)/'Google/Chrome/Application/chrome.exe')]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():return str(candidate)
    raise BlockedError('No Chromium browser available for required desktop/mobile QA')

def check(project):
    node=shutil.which('node') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'nodejs/node.exe')
    if not Path(node).is_file():raise BlockedError('Node is required for viewer QA')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    profile=project.path('.cache/browser-profile');profile.mkdir(exist_ok=True)
    flags=[browser(),'--headless=new',f'--remote-debugging-port={port}','--remote-debugging-address=127.0.0.1',f'--user-data-dir={profile}',
           '--no-first-run','--no-default-browser-check','--disable-background-networking','--enable-unsafe-swiftshader','--use-angle=swiftshader','about:blank']
    process=subprocess.Popen(flags,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        result=subprocess.run([node,str(Path(__file__).parent/'test_viewer.mjs'),str(project.root),str(port)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=100)
        log=project.path('validation/execution/viewer_qa.txt');log.parent.mkdir(exist_ok=True)
        log.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8',newline='\n')
        if result.returncode:raise GateError(f'Browser QA failed ({result.returncode}): {result.stderr[-1500:]}')
        report=read_json(project.path('validation/viewer_qa.json',exists=True))
        if report['status']!='PASS' or report['glb_sha256']!=digest_file(project.glb):raise GateError('Browser QA is stale/failed')
        return report
    finally:
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.terminate()
