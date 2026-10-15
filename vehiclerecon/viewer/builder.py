"""A viewer is a wrapper around the exact verified GLB bytes."""
import base64,html,json,re,hashlib
from pathlib import Path
from ..core.errors import GateError
from ..core.project import read_json
from ..core.manifest import digest_file,write_json

def embedded_bytes(text):
    match=re.search(r'const GLB_BASE64="([A-Za-z0-9+/=]+)"',text)
    if not match:raise GateError('Viewer has no embedded GLB')
    return base64.b64decode(match.group(1),validate=True)

def build(project):
    geometry=read_json(project.path('validation/glb_geometry_report.json',exists=True))
    if geometry['status']!='PASS' or geometry['glb_sha256']!=digest_file(project.glb):
        raise GateError('Viewer requires a current verified GLB')
    config=project.data['viewer'];raw=project.glb.read_bytes()
    template=(Path(__file__).parent/'viewer_template.html').read_text(encoding='utf-8')
    layers=''.join('<button data-group="'+html.escape(g['id'],quote=True)+'" aria-pressed="true">'+html.escape(g['label'])+'</button>' for g in config['groups'])
    text=template.replace('__GLB_BASE64__',base64.b64encode(raw).decode()).replace('__GLB_SHA256__',geometry['glb_sha256'])
    text=text.replace('__TITLE__',html.escape(config['title'])).replace('__EYEBROW__',html.escape(config['eyebrow'])).replace('__LAYERS_HTML__',layers)
    text=text.replace('__VIEWER_CONFIG__',json.dumps(config,ensure_ascii=True).replace('<','\\u003c'))
    if embedded_bytes(text)!=raw:raise GateError('Viewer embedding altered exported bytes')
    project.path('output/viewer.html').write_text(text,encoding='utf-8',newline='\n')
    result={'status':'PASS','glb_sha256':geometry['glb_sha256'],'embedded_glb_sha256':hashlib.sha256(embedded_bytes(text)).hexdigest(),'exact_embedded_glb':True}
    write_json(project.path('validation/viewer_build.json'),result)
    return result
