"""Package the exact exported GLB in a dependency-free local HTML viewer."""
from pathlib import Path
import base64,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'validation/report.json').read_text())
geometry=json.loads((ROOT/'validation/glb_geometry_report.json').read_text())
assert report['silhouette_pass'] and report['surface_quality_pass'] and geometry['status']=='PASS'
glb=(ROOT/'exports/tesla_surface_model.glb').read_bytes();digest=hashlib.sha256(glb).hexdigest()
assert digest==geometry['glb_sha256']
template=(ROOT/'scripts/viewer_template.html').read_text(encoding='utf-8')
html=template.replace('__GLB_BASE64__',base64.b64encode(glb).decode()).replace('__GLB_SHA256__',digest)
(ROOT/'exports/viewer.html').write_text(html,encoding='utf-8')
print('VIEWER_PACKAGED',len(html.encode()),'bytes; embedded GLB SHA256',digest)
