import threading
import httpx
import uvicorn
import webbrowser
from vehiclerecon.cli import main


def test_cli_launch_binds_ephemeral_loopback_bootstraps_browser_and_stops(tmp_path,monkeypatch,capsys):
    servers=[];opened=[];ready=threading.Event();result=[]
    original=uvicorn.Server
    class RecordingServer(original):
        def run(self,sockets=None):
            servers.append(self);return super().run(sockets=sockets)
    monkeypatch.setattr(uvicorn,'Server',RecordingServer)
    def open_browser(url):opened.append(url);ready.set();return True
    monkeypatch.setattr(webbrowser,'open',open_browser)
    thread=threading.Thread(target=lambda:result.append(main(['studio','--root',str(tmp_path)])),daemon=True)
    thread.start()
    try:
        assert ready.wait(15)
        origin,fragment=opened[0].split('/#bootstrap=')
        assert origin.startswith('http://127.0.0.1:')
        with httpx.Client(base_url=origin,trust_env=False) as client:
            assert client.get('/').status_code==200
            assert client.get('/api/v1/projects').status_code==401
            response=client.post('/api/v1/session/bootstrap',json={'secret':fragment},headers={'Origin':origin})
            assert response.status_code==200
            assert client.get('/api/v1/projects').json()==[]
            with client.stream('GET','/api/v1/events?tab_id='+'a'*32,timeout=5) as stream:
                lines=stream.iter_lines();assert next(lines).startswith('id:')
                for server in servers:server.should_exit=True
                list(lines)  # The live stream finishes before the client closes it.
    finally:
        for server in servers:server.should_exit=True
        thread.join(15)
    assert not thread.is_alive() and result==[0]
    assert fragment not in capsys.readouterr().out
