"""Apply reviewed cowl and wheel corrections to the detailed milestone."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import bmesh

for ob in list(bpy.data.objects):
    if ob.name.startswith('TAIL_RETURN_') or ob.name=='PILLAR_A_FOOT':bpy.data.objects.remove(ob,do_unlink=True)
for ob in bpy.data.objects:
    if ob.type=='MESH' and ob.name.startswith('AERO_SPOKE_') and ('_FR_' in ob.name or '_RR_' in ob.name):
        if ob.data.polygons[0].normal.y<0:
            bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()

for ob in bpy.data.objects:
    if ob.type=='MESH' and ob.name.startswith('BRAKE_DISC_'):
        sign=-1 if ob.name.endswith('L') else 1
        for vertex in ob.data.vertices:vertex.co.y=sign*.088

def authored(points):
    pts=[Vector(v) for v in points];d=[0.]
    for a,b in zip(pts,pts[1:]):d.append(d[-1]+(b-a).length)
    d=[v/d[-1] for v in d];slopes=[]
    for i in range(len(pts)):
        a=max(0,i-1);b=min(len(pts)-1,i+1);slopes.append((pts[b]-pts[a])/(d[b]-d[a]))
    def sample(t):
        if t<=0:return pts[0].copy()
        if t>=1:return pts[-1].copy()
        i=next(i for i in range(len(pts)-1) if d[i]<=t<=d[i+1]);h=d[i+1]-d[i];u=(t-d[i])/h
        return (2*u**3-3*u*u+1)*pts[i]+(u**3-2*u*u+u)*h*slopes[i]+(-2*u**3+3*u*u)*pts[i+1]+(u**3-u*u)*h*slopes[i+1]
    return sample
def p(u,y,v):return Vector((sx(u),y,sz(v)))
bottom=authored([p(623,0,577),p(623,.4,579),p(623,.78,582)])
a=p(623,0,577);b=p(633,.74,579);top=authored([a,(a+b)/2+Vector((0,0,.012)),b])
ob=bpy.data.objects['COWL_TRANSITION'];us=list(ob['grid_us']);vs=list(ob['grid_vs'])
verts=[bottom(u).lerp(top(u),v) for v in vs for u in us];faces=[]
for j in range(len(vs)-1):
    for i in range(len(us)-1):
        k=j*len(us)+i;faces.append((k,k+len(us),k+len(us)+1,k+1))
ob.data.clear_geometry();ob.data.from_pydata(verts,[],faces)
for face in ob.data.polygons:face.use_smooth=True
ob.data.update()
# Integrate the final cowl bridge into the fender's existing quad boundary.
# This closes the gap left by independently parameterized hood and fender
# rails; it is geometry joined to the fender, not a seam-covering stroke.
fender=bpy.data.objects['FENDER_FRONT']
if not fender.get('cowl_bridge_integrated'):
    def cage_x(name,x):
        pts=bpy.data.objects['CAGE_'+name].data.splines[0].bezier_points
        for aa,bb in zip(pts,pts[1:]):
            if aa.co.x<=x<=bb.co.x:
                lo=0.;hi=1.
                for _ in range(32):
                    t=(lo+hi)/2;q=aa.co*(1-t)**3+aa.handle_right*3*t*(1-t)**2+bb.handle_left*3*t*t*(1-t)+bb.co*t**3
                    if q.x<x:lo=t
                    else:hi=t
                return q
        return pts[-1].co.copy()
    fu=list(fender['grid_us']);fv=list(fender['grid_vs']);indices=[i for i,u in enumerate(fu) if .6249<=u<=.7501]
    bm=bmesh.new();bm.from_mesh(fender.data);bm.verts.ensure_lookup_table()
    bottom=[bm.verts[(len(fv)-1)*len(fu)+i] for i in indices]
    top=[cage_x('L02_HOOD_SHOULDER_R',sx(580.3+(623-580.3)*j/(len(indices)-1))) for j in range(len(indices))]
    previous=bottom
    for fraction in (.33,.66,.98,1.):
        row=[bm.verts.new(v.co.lerp(q,fraction)) for v,q in zip(bottom,top)]
        for j in range(len(row)-1):
            face=bm.faces.new((previous[j],previous[j+1],row[j+1],row[j]));face.normal_update()
            if face.normal.dot(Vector((0,1,1)))<0:face.normal_flip()
        previous=row
    bm.to_mesh(fender.data);bm.free();fender.data.update();fender['cowl_bridge_integrated']=True
us=[0,.025,.25,.5,.75,.975,1];vs=us
a=p(623,.78,582);b=p(633,.74,579);c=p(635,.86,589);d=p(623,.86,589)
verts=[a*(1-u)*(1-v)+b*u*(1-v)+c*u*v+d*(1-u)*v for v in vs for u in us]
faces=[]
for j in range(6):
    for i in range(6):
        k=j*7+i;faces.append((k,k+1,k+8,k+7))
foot=mesh('PILLAR_A_FOOT',verts,faces,bpy.data.materials['MAT_BODY_SURFACE'],'03_BODY');foot.parent=bpy.data.objects['BODY_MASTER']
m=foot.modifiers.new('Symmetry','MIRROR');m.use_axis[0]=False;m.use_axis[1]=True
m=foot.modifiers.new('Pillar fairing','SUBSURF');m.levels=1;m.render_levels=2
m=foot.modifiers.new('Pillar wall','SOLIDIFY');m.thickness=.002

# Lamp return bodies follow the rear corner, beyond the continuous bar.
red=bpy.data.materials['MAT_LIGHT_REAR'];black=bpy.data.materials['MAT_TRIM']
for label,sgn in [('L',-1),('R',1)]:
    points=[(2.30,sgn*.67,1.025),(2.24,sgn*.81,1.025),(2.265,sgn*.82,.953),(2.31,sgn*.69,.950)]
    curve('TAIL_RETURN_HOUSING_'+label,points,black,.011,'06_LIGHTS')
    curve('TAIL_RETURN_LENS_'+label,[(x+.004,y,z) for x,y,z in points],red,.0055,'06_LIGHTS')
save();print('REVIEW_CORRECTIONS_APPLIED: cowl boundary continuous; brake discs behind spokes')
