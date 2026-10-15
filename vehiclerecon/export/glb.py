from ..core.project import read_json
from ..validation.report import review
from ..blender.runner import run

def export(project,*,executable=None):
    audit=read_json(project.path('validation/geometry_audit.json',exists=True))
    review(project,audit['geometry_hash'])
    return run(project,'export',source=project.blend,executable=executable)
