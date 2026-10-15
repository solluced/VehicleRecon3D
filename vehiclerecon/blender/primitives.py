"""Parameterized annular and fan blockout adapters."""
import bpy,math
from .geometry import mesh
from .surfaces import finish

def build_blockout(project,config):
    from ..details.wheel_arches import liner as liner_mesh
    from ..details.wheels import revolved
    geometry=project.generated('calibration',check=False)['wheel_geometry']
    for axle in geometry['axles']:
        liner=config['liner'];vertices,faces=liner_mesh(axle,liner)
        obj=mesh(liner['name'].format(axle=axle['id'].upper()),vertices,faces,liner['material'],liner['collection'])
        finish(obj,liner['settings'])
    tire=config['tire']
    profile=[(r*geometry['radius_m'],y) for r,y in tire['profile']]
    vertices,faces=revolved(profile,tire['segments']);base=None
    axles={a['id']:a for a in geometry['axles']}
    for binding in config['wheels']:
        axle=axles[binding['axle']];side=binding['side'];label=binding['label']
        obj=mesh(tire['name'].format(label=label),vertices,faces,tire['material'],tire['collection'])
        if base is None:base=obj.data
        else:obj.data=base
        obj.location=(axle['x'],side*axle['track_m']/2,axle['z'])
        disc=config['disc'];n=disc['segments']
        verts=[(0,side*disc['depth'],0)]+[(disc['radius']*math.cos(i*math.tau/n),side*disc['depth'],disc['radius']*math.sin(i*math.tau/n)) for i in range(n)]
        cap=mesh(disc['name'].format(label=label),verts,[(0,i+1,(i+1)%n+1) for i in range(n)],disc['material'],tire['collection']);cap.location=obj.location
