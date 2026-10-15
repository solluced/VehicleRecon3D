import math

def liner(axle,config):
    count=config['segments']
    vertices=[(axle['x'],config['depth'],config['center_height'])]+[(axle['x']+config['radius']*math.cos(a),config['depth'],axle['z']+config['radius']*math.sin(a)) for a in [math.radians(config['start_angle']+i*config['span']/count) for i in range(count+1)]]
    return vertices,[(0,i+1,i+2) for i in range(count)]
