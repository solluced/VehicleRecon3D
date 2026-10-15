import bpy
import numpy as np
from ..reference.overlay_extract import extract
from ..core.manifest import write_json,digest_file

def build(project):
    path=project.path(project.data['references']['control_overlay'],exists=True)
    image=bpy.data.images.load(str(path),check_existing=True);width,height=image.size
    rgb=np.array(image.pixels[:],dtype=np.float32).reshape(height,width,4)[::-1,:,:3]
    result=extract(rgb);result['source_sha256']=digest_file(path);result['image_size']=[width,height]
    write_json(project.path('generated/overlay_raw.json'),result)
