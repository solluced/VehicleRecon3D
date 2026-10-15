"""Host rendering requests, all routed through the shared Blender runner."""
from ..blender.runner import run

def presentation(project,source):
    return run(project,'presentation',source=source)
