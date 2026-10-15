"""Pure curve-record expansion, independent of a vehicle or Blender."""
import math
from ..core.errors import ReferenceError,SchemaError

def mirrored(points,axis=1,*,reverse=False):
    result=[tuple(-value if i==axis else value for i,value in enumerate(p)) for p in points]
    return result[::-1] if reverse else result

def expand(config,geometry):
    result=[]
    for record in config['curves']:
        if record.get('landmark') and record['landmark'] not in config['landmarks']:
            raise ReferenceError(f"Unknown cage landmark: {record['landmark']}")
        if record['symmetry']:
            for side,sign in config['sides']:
                entry=dict(record,id=record['id']+'_'+side,
                           points=[(p[0],sign*p[1],p[2]) for p in record['points']])
                result.append(entry)
        else:
            result.append(record)
    axles={a['id']:a for a in geometry['axles']}
    for guide in config['guides']:
        for axle_id in guide['axles']:
            if axle_id not in axles:
                raise ReferenceError(f'Unknown guide axle: {axle_id}')
            axle=axles[axle_id]
            for side,sign in config['sides']:
                points=[]
                angles=[i*math.tau/guide['segments'] for i in range(guide['segments'])] if guide['kind']=='wheel' else [math.radians(a) for a in guide['angles_deg']]
                radius=geometry['radius_m'] if guide['kind']=='wheel' else guide['radius_m']
                for angle in angles:
                    y=axle['track_m']/2 if guide['kind']=='wheel' else guide['half_width_m']+guide['width_crown_m']*max(0,math.sin(angle))
                    points.append((axle['x']+radius*math.cos(angle),sign*y,axle['z']+radius*math.sin(angle)))
                result.append({'id':guide['name'].format(axle=axle_id.upper(),side=side),'points':points,
                               'material':guide['material'],'radius':guide['radius'],'cyclic':guide['kind']=='wheel','handles':'AUTO','role':guide['kind'],'kind':guide['kind']})
    names=[r['id'] for r in result]
    if len(names)!=len(set(names)):
        raise SchemaError('Duplicate expanded cage ID')
    return result
