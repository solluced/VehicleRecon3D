"""Parameterized annular and fan blockout adapters."""
import bpy,math
from .geometry import mesh
from .surfaces import finish

def revolved(profile,segments):
    vertices=[];faces=[]
    for radius,y in profile:
        for i in range(segments):
            a=i*math.tau/segments;vertices.append((radius*math.cos(a),y,radius*math.sin(a)))
    for j in range(len(profile)):
        for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,((j+1)%len(profile))*segments+(i+1)%segments,((j+1)%len(profile))*segments+i))
    return vertices,faces

def build_blockout(project,config):
    geometry=project.generated('calibration',check=False)['wheel_geometry']
    for axle in geometry['axles']:
        liner=config['liner'];count=liner['segments']
        vertices=[(axle['x'],liner['depth'],liner['center_height'])]+[(axle['x']+liner['radius']*math.cos(a),liner['depth'],axle['z']+liner['radius']*math.sin(a)) for a in [math.radians(liner['start_angle']+i*liner['span']/count) for i in range(count+1)]]
        obj=mesh(liner['name'].format(axle=axle['id'].upper()),vertices,[(0,i+1,i+2) for i in range(count)],liner['material'],liner['collection'])
        finish(obj,liner['settings'])
    tire=config['tire'];vertices,faces=revolved(tire['profile'],tire['segments']);base=None
    axles={a['id']:a for a in geometry['axles']}
    for binding in config['wheels']:
        axle=axles[binding['axle']];side=binding['side'];label=binding['label']
        obj=mesh('WHEEL_'+label,vertices,faces,tire['material'],tire['collection'])
        if base is None:base=obj.data
        else:obj.data=base
        obj.location=(axle['x'],side*axle['track_m']/2,axle['z'])
        disc=config['disc'];n=disc['segments']
        verts=[(0,side*disc['depth'],0)]+[(disc['radius']*math.cos(i*math.tau/n),side*disc['depth'],disc['radius']*math.sin(i*math.tau/n)) for i in range(n)]
        cap=mesh(disc['name'].format(label=label),verts,[(0,i+1,(i+1)%n+1) for i in range(n)],disc['material'],tire['collection']);cap.location=obj.location
