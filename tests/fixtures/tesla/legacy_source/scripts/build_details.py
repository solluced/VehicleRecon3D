"""Geometric cavities, separate panels/glass, aero wheels and basic interior.

Run only after reviewing the body milestone. Cavities delete actual body
faces and retain quad boundary loops, with recessed mesh housings behind.
"""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import bmesh

report=json.loads((ROOT/'validation/report.json').read_text())
assert report.get('silhouette_pass'), 'Details require the basic silhouette gate.'
assert 'DOOR_F' in bpy.data.objects, 'Run on the undetailed surface milestone only.'
BODY=bpy.data.materials['MAT_BODY_SURFACE']; BLACK=bpy.data.materials['MAT_TRIM']
RIM=mat('MAT_RIM',(.055,.065,.08),.26,.85)
MACHINED=mat('MAT_MACHINED',(.31,.36,.41),.2,.95)
BRAKE=mat('MAT_BRAKE',(.08,.09,.10),.4,.8)
LENS=mat('MAT_LIGHT_FRONT',(.018,.025,.034),.12,.4)
RED=mat('MAT_LIGHT_REAR',(.40,.002,.004),.18,.25)
bsdf=RED.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Emission Color'].default_value=(.4,.001,.002,1); bsdf.inputs['Emission Strength'].default_value=1.2
LED=emissive('MAT_DRL',(.76,.86,1)); SEAT=mat('MAT_INTERIOR',(.055,.065,.075),.62)

def flip(me):
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
def subdiv(ob,n=1):
    m=ob.modifiers.new('Detail smoothing','SUBSURF'); m.levels=n; m.render_levels=n
def mirror(ob):
    m=ob.modifiers.new('Symmetry','MIRROR'); m.use_axis[0]=False; m.use_axis[1]=True
def split(ob,name_left,name_right):
    for mod in list(ob.modifiers):
        if mod.type=='MIRROR': ob.modifiers.remove(mod)
    ob.name=name_right
    left=ob.copy(); left.data=ob.data.copy(); coll(ob.users_collection[0].name).objects.link(left); left.name=name_left
    for v in left.data.vertices:v.co.y*=-1
    flip(left.data)
    return left,ob
def box(name,location,size,material=BLACK,collection='06_LIGHTS',bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    ob=bpy.context.object; ob.name=name; ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move(ob,collection); ob.data.materials.append(material)
    for p in ob.data.polygons:p.use_smooth=True
    if bevel:
        m=ob.modifiers.new('Edge radii','BEVEL'); m.width=bevel; m.segments=3
        m=ob.modifiers.new('Face normals','WEIGHTED_NORMAL'); m.keep_sharp=True
    return ob

def cavity(source,name,predicate,material,offset,collection='06_LIGHTS',symmetric=True):
    ob=bpy.data.objects[source]; me=ob.data
    us=list(ob['grid_us']); vs=list(ob['grid_vs']); nx=len(us)-1
    if 'patch_u' not in me.attributes:
        ua=me.attributes.new('patch_u','FLOAT','FACE'); va=me.attributes.new('patch_v','FLOAT','FACE')
        for face in me.polygons:
            j,i=divmod(face.index,nx)
            ua.data[face.index].value=(us[i]+us[i+1])/2;va.data[face.index].value=(vs[j]+vs[j+1])/2
    ua=me.attributes['patch_u'].data;va=me.attributes['patch_v'].data
    selected=[]
    for face in me.polygons:
        u=ua[face.index].value;v=va[face.index].value
        if predicate(u,v): selected.append(face.index)
    assert selected,(source,name)
    used=sorted({v for i in selected for v in me.polygons[i].vertices}); remap={old:new for new,old in enumerate(used)}
    verts=[me.vertices[i].co+Vector(offset) for i in used]
    faces=[tuple(remap[v] for v in me.polygons[i].vertices) for i in selected]
    housing=mesh(name,verts,faces,material,collection); subdiv(housing)
    thick=housing.modifiers.new('Recessed lens thickness','SOLIDIFY'); thick.thickness=.004
    if symmetric:mirror(housing)
    # Record an actual rim edge for a DRL, before deleting the body faces.
    maxrow=max(i//len(us) for i in used)
    edge=[me.vertices[i].co+Vector(offset)+Vector((0,0,.003)) for i in used if i//len(us)==maxrow]
    bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[i] for i in selected],context='FACES')
    crease=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    for e in bm.edges:
        if e.is_boundary:e[crease]=.72
    bm.to_mesh(me); bm.free(); me.update()
    housing['construction']='Recessed housing behind a real opening cut from the body quad patch'
    return housing,edge

head,edge=cavity('NOSE_CHEEK','LIGHT_HEAD',lambda u,v:.02<u<.98 and .04<v<.65,LENS,(0,-.003,-.004))
split(head,'LIGHT_HEAD_L','LIGHT_HEAD_R')
for label,sgn in [('L',-1),('R',1)]:
    curve('LED_HEAD_'+label,[(v.x,sgn*v.y,v.z) for v in edge],LED,.0026,'06_LIGHTS')

intake,_=cavity('BUMPER_FRONT','INTAKE_CENTER',lambda u,v:u<.69 and .04<v<.34,BLACK,(.025,0,0))
side_inlet,_=cavity('BUMPER_FRONT','INTAKE_SIDE',lambda u,v:.74<u<.988 and .20<v<.52,BLACK,(.018,-.003,0))
split(side_inlet,'INTAKE_SIDE_L','INTAKE_SIDE_R')
for z in (.285,.325,.365):
    curve('GRILLE_SLAT', [(-2.26,-.59,z),(-2.35,-.35,z),(-2.365,0,z),(-2.35,.35,z),(-2.26,.59,z)],RIM,.003,'06_LIGHTS')

tails,_=cavity('REAR_HATCH','LIGHT_TAIL',lambda u,v:u<.988 and .84<v<.988,RED,(.006,0,0))
split(tails,'LIGHT_TAIL_L','LIGHT_TAIL_R')
diffuser,_=cavity('BUMPER_REAR','DIFFUSER_REAR',lambda u,v:u<.96 and v<.46,BLACK,(-.015,0,0))
for y in (-.55,-.28,0,.28,.55):
    box('DIFFUSER_FIN',(2.19,y,.20),(.14,.014,.05),BLACK,bevel=.006)

# Separate left/right doors, with genuine three-millimeter seams and inner
# backing skins. No texture linework is used for panel boundaries.
for base,left,right in [('DOOR_F','DOOR_FL','DOOR_FR'),('DOOR_R','DOOR_RL','DOOR_RR')]:
    ob=bpy.data.objects[base]
    xmin=min(v.co.x for v in ob.data.vertices); xmax=max(v.co.x for v in ob.data.vertices); mid=(xmin+xmax)/2
    for v in ob.data.vertices:
        v.co.x=mid+(v.co.x-mid)*(1-.003/(xmax-xmin))
    doors=split(ob,left,right)
    for door in doors:
        skin=door.copy(); skin.data=door.data.copy(); coll('04_PANELS').objects.link(skin); skin.name='INNER_'+door.name
        skin.data.materials.clear(); skin.data.materials.append(BLACK)
        for v in skin.data.vertices:v.co.y-=math.copysign(.008,v.co.y)
for base,left,right in [('GLASS_FRONT','GLASS_FRONT_LEFT','GLASS_FRONT_RIGHT'),('GLASS_REAR_SIDE','GLASS_REAR_LEFT','GLASS_REAR_RIGHT')]:
    split(bpy.data.objects[base],left,right)
for name in ('FRAME_BACK_GLASS_FRONT','FRAME_FRONT_GLASS_REAR_SIDE','PILLAR_B'):
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
pillar=mesh('PILLAR_B',[(sx(801),.716,sz(576)),(sx(822),.715,sz(575)),(sx(822),.610,sz(524)),(sx(801),.610,sz(524))],[(0,1,2,3)],BLACK,'03_BODY')
mirror(pillar)
m=pillar.modifiers.new('Pillar thickness','SOLIDIFY');m.thickness=.005
m=pillar.modifiers.new('Pillar edge radius','BEVEL');m.width=.002;m.segments=2
for label,u in [('F',782),('R',932)]:
    for side,sgn in [('L',-1),('R',1)]:
        box('HANDLE_'+label+side,(sx(u),sgn*.935,sz(602 if label=='F' else 592)),(.20,.012,.028),RIM,'04_PANELS',.009)

# Mirror housings use shaped quad shells. Their positions are inferred from
# the side A-pillar and the top view; reference end-view mirrors disagree.
for label,sgn in [('L',-1),('R',1)]:
    stem=curve('MIRROR_STEM_'+label,[(sx(648),sgn*.77,1.04),(sx(650),sgn*.88,1.06)],BLACK,.013,'04_PANELS')
    ob=box('MIRROR_'+label,(sx(653),sgn*.900,1.105),(.24,.105,.12),BODY,'04_PANELS',.035)
    box('MIRROR_GLASS_'+label,(sx(653)+.116,sgn*.900,1.105),(.006,.088,.084),MACHINED,'05_GLASS',.012)

# Ten swept aero spokes per wheel, rim barrels and machined lip rings.
def cylinder(name,radius,depth,location,material,parent):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=location,rotation=(math.pi/2,0,0))
    ob=bpy.context.object; ob.name=name; move(ob,'07_WHEELS'); ob.data.materials.append(material); ob.parent=parent
    for poly in ob.data.polygons:poly.use_smooth=True
    return ob
for label in ('FL','FR','RL','RR'):
    tire=bpy.data.objects['WHEEL_'+label]; center=tire.location.copy(); side=-1 if label.endswith('L') else 1
    tire.name='TIRE_'+label
    root=bpy.data.objects.new('WHEEL_'+label,None); coll('07_WHEELS').objects.link(root); root.location=center
    tire.parent=root; tire.location=(0,0,0)
    disc=bpy.data.objects['WHEEL_BLOCKOUT_DISC_'+label]; disc.name='BRAKE_DISC_'+label; disc.parent=root; disc.location=(0,0,0)
    disc.data=disc.data.copy();disc.data.materials.clear();disc.data.materials.append(BRAKE)
    for vertex in disc.data.vertices:vertex.co.y=side*.088
    ringverts=[]; ringfaces=[]
    profile=[(.293,side*.095),(.312,side*.095),(.317,side*.106),(.313,side*.115),(.296,side*.115),(.291,side*.107)]
    for r,y in profile:
        for i in range(64):
            a=i*math.tau/64; ringverts.append((r*math.cos(a),y,r*math.sin(a)))
    for j in range(6):
        for i in range(64):ringfaces.append((j*64+i,j*64+(i+1)%64,((j+1)%6)*64+(i+1)%64,((j+1)%6)*64+i))
    rim=mesh('RIM_'+label,ringverts,ringfaces,MACHINED,'07_WHEELS');rim.parent=root
    for i in range(10):
        a=i*math.tau/10
        coords=[(.075,-.10),(.294,.15),(.304,.44),(.133,.31)]
        poly=[(r*math.cos(a+q),side*.110,r*math.sin(a+q)) for r,q in coords]
        blade=mesh('AERO_SPOKE_'+label+'_'+str(i+1),poly,[(0,1,2,3)],RIM,'07_WHEELS'); blade.parent=root
        if side>0:flip(blade.data)
        mod=blade.modifiers.new('Spoke depth','SOLIDIFY');mod.thickness=.018
        mod=blade.modifiers.new('Spoke radii','BEVEL');mod.width=.005;mod.segments=3
        mod=blade.modifiers.new('Spoke normals','WEIGHTED_NORMAL')
    cylinder('HUB_'+label,.069,.018,(0,side*.118,0),RIM,root)
    cylinder('CENTER_CAP_'+label,.037,.004,(0,side*.125,0),MACHINED,root)
    for i in range(5):
        a=i*math.tau/5;cylinder('LUG_'+label,.007,.009,(.049*math.cos(a),side*.126,.049*math.sin(a)),MACHINED,root)

# Basic visible interior; exterior remains the priority.
for side in (-1,1):
    box('FRONT_SEAT_BASE',(-.1,side*.42,.46),(.48,.44,.15),SEAT,'08_INTERIOR',.07)
    back=box('FRONT_SEAT_BACK',(.13,side*.42,.83),(.14,.45,.58),SEAT,'08_INTERIOR',.065);back.rotation_euler.y=-.12
    box('FRONT_HEADREST',(.18,side*.42,1.17),(.13,.28,.19),SEAT,'08_INTERIOR',.045)
box('REAR_BENCH',(.98,0,.49),(.48,1.25,.18),SEAT,'08_INTERIOR',.07)
box('REAR_BACKREST',(1.2,0,.82),(.14,1.25,.48),SEAT,'08_INTERIOR',.07)
box('DASHBOARD',(-.83,0,.94),(.23,1.27,.15),BLACK,'08_INTERIOR',.045)
box('CENTER_CONSOLE',(-.10,0,.61),(.73,.19,.18),BLACK,'08_INTERIOR',.035)
box('CENTER_DISPLAY',(-.67,0,1.12),(.025,.32,.19),BLACK,'08_INTERIOR',.009)
bpy.ops.mesh.primitive_torus_add(major_radius=.14,minor_radius=.012,major_segments=48,minor_segments=12,location=(-.60,-.42,.98),rotation=(0,math.pi/2,0))
steering=bpy.context.object;steering.name='STEERING_WHEEL';move(steering,'08_INTERIOR');steering.data.materials.append(BLACK)
box('CABIN_FLOOR',(.3,0,.22),(2.8,1.46,.05),BLACK,'08_INTERIOR',.015)

# A logical master retains the independent editable body patches.
master=bpy.data.objects.new('BODY_MASTER',None);coll('03_BODY').objects.link(master)
master['construction']='Editable quad patch assembly; independent panels retain SubD modifiers'
for col in ('03_BODY','04_PANELS'):
    for ob in list(coll(col).objects):
        if ob!=master and ob.parent is None:ob.parent=master

s=bpy.context.scene;s['model_status']='DETAILED_MODEL_PENDING_FINAL_SURFACE_REVIEW';s['export_allowed']=False
save()
print('DETAIL_GEOMETRY_SAVED; final masks and reflection review still required')
