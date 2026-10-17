"""Same-origin local sessions and bounded ASGI input; no permissive CORS."""
from dataclasses import dataclass, field
from pathlib import Path
import secrets
import time
from starlette.responses import JSONResponse


@dataclass
class Config:
    roots: tuple
    port: int
    host: str = '127.0.0.1'
    bootstrap: str = field(default_factory=lambda:secrets.token_urlsafe(32),repr=False)
    created: float = field(default_factory=time.monotonic)
    static: Path = field(default_factory=lambda:Path(__file__).parent/'static')
    max_upload: int = 64*1024*1024
    max_pixels: int = 64*1000*1000
    workspace_quota: int = 512*1024*1024

    def __post_init__(self):
        if self.host!='127.0.0.1':raise ValueError('Studio binds only to 127.0.0.1')
        if not 1<=self.port<=65535:raise ValueError('A bound local port is required')
        self.roots=tuple(Path(p).resolve(strict=True) for p in self.roots)
        if not self.roots or any(not p.is_dir() for p in self.roots):raise ValueError('Existing allowed project roots required')

    @property
    def origin(self):return f'http://127.0.0.1:{self.port}'


class Security:
    def __init__(self, app, *, config, sessions):
        self.app=app;self.config=config;self.sessions=sessions

    async def __call__(self, scope, receive, send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers={k.decode().lower():v.decode() for k,v in scope['headers']}
        method=scope['method'];path=scope['path'];api=path.startswith('/api/')
        def error(code,message):return JSONResponse({'code':'SECURITY','message':message,'issues':[]},status_code=code)
        rejection=None
        if headers.get('host')!=self.config.origin.removeprefix('http://'):
            rejection=error(403,'Unexpected Host')
        elif headers.get('origin') not in (None,self.config.origin):
            rejection=error(403,'Unexpected Origin')
        elif headers.get('sec-fetch-site') in ('cross-site','same-site'):
            rejection=error(403,'Cross-site request rejected')
        elif method not in ('GET','HEAD') and headers.get('origin')!=self.config.origin:
            rejection=error(403,'Exact Origin required')
        from http.cookies import SimpleCookie
        cookies=SimpleCookie()
        try:cookies.load(headers.get('cookie',''))
        except Exception:pass
        token=cookies.get('vr_session');session=self.sessions.get(token.value if token else '')
        if rejection is None and api and path!='/api/v1/session/bootstrap':
            if session is None or time.monotonic()-session['created']>12*3600:rejection=error(401,'Local session required')
            elif method not in ('GET','HEAD') and not secrets.compare_digest(headers.get('x-csrf-token',''),session['csrf']):
                rejection=error(403,'CSRF token required')
        scope['studio_session']=session
        if rejection:return await rejection(scope,receive,send)
        if method not in ('GET','HEAD'):
            limit=self.config.max_upload if path.endswith('/reference-imports') else 2*1024*1024
            chunks=[];size=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect':return
                size+=len(message.get('body',b''))
                if size>limit:return await error(413,'Request exceeds size budget')(scope,receive,send)
                chunks.append(message.get('body',b''))
                if not message.get('more_body'):break
            body=b''.join(chunks);del chunks
            consumed=False
            original_receive=receive
            async def bounded_receive():
                nonlocal consumed
                if not consumed:consumed=True;return {'type':'http.request','body':body,'more_body':False}
                return await original_receive()
            receive=bounded_receive
        async def secured_send(message):
            if message['type']=='http.response.start':
                message['headers']+= [(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer'),
                    (b'cache-control',b'no-store'),(b'x-frame-options',b'DENY'),
                    (b'content-security-policy',b"default-src 'self'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]
            await send(message)
        return await self.app(scope,receive,secured_send)
