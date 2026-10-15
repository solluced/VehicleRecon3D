"""Feature-controlled quad patch construction from the authored cage.

Independent hood, fender annuli, door, greenhouse and fascia patches. No
whole-body loft or single outer-profile formula. Stage is body blockout;
detail/export gates remain closed until rendered silhouette comparison.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
import bmesh
from mathutils.geometry import interpolate_bezier

def p(u,y,v): return Vector((sx(u),y,sz(v)))
BODY=mat('MAT_BODY_SURFACE',(.77,.80,.84),.29,.12)
GLASS=mat('MAT_GLASS',(.018,.027,.04),.15,.12)
GLASS.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.32
BLACK=mat('MAT_TRIM',(.012,.017,.022),.32)
TIRE=mat('MAT_TIRE',(.012,.014,.017),.65)

for col in ('02_BLOCKOUT','03_BODY','04_PANELS','05_GLASS','06_LIGHTS','07_WHEELS','08_INTERIOR'):
    for ob in list(coll(col).objects): bpy.data.objects.remove(ob,do_unlink=True)
for ob in coll('01_CURVE_CAGE').objects: ob.hide_render=True; ob.hide_set(True)
for ob in coll('00_REFERENCE').objects: ob.hide_render=True; ob.hide_set(True)

bpy.context.view_layer.update()
def cubic(a,b,c,d,t): return a*(1-t)**3+3*b*t*(1-t)**2+3*c*t*t*(1-t)+d*t**3
def at_x(name,x):
    sp=bpy.data.objects['CAGE_'+name].data.splines[0]
    points=sp.bezier_points
    if x<=points[0].co.x: return points[0].co.copy()
    if x>=points[-1].co.x: return points[-1].co.copy()
    for a,b in zip(points,points[1:]):
        if a.co.x<=x<=b.co.x:
            lo=0.; hi=1.
            for _ in range(30):
                t=(lo+hi)/2; q=cubic(a.co,a.handle_right,b.handle_left,b.co,t)
                if q.x<x: lo=t
                else: hi=t
            return q
def rail(name,a,b): return lambda t: at_x(name,sx(a+(b-a)*t))

def authored(points):
    # Chord-parameterized Hermite boundary through authored geometric events.
    pts=[Vector(v) for v in points]
    distances=[0.]
    for a,b in zip(pts,pts[1:]): distances.append(distances[-1]+(b-a).length)
    distances=[v/distances[-1] for v in distances]
    slopes=[]
    for i,q in enumerate(pts):
        a=max(0,i-1); b=min(len(pts)-1,i+1)
        slopes.append((pts[b]-pts[a])/(distances[b]-distances[a]))
    def sample(t):
        if t<=0:return pts[0].copy()
        if t>=1:return pts[-1].copy()
        i=next(i for i in range(len(pts)-1) if distances[i]<=t<=distances[i+1])
        h=distances[i+1]-distances[i]; u=(t-distances[i])/h
        return (2*u**3-3*u*u+1)*pts[i]+(u**3-2*u*u+u)*h*slopes[i]+(-2*u**3+3*u*u)*pts[i+1]+(u**3-u*u)*h*slopes[i+1]
    return sample

def coons(bottom,top,left=None,right=None):
    a=bottom(0); b=bottom(1); c=top(0); d=top(1)
    left=left or (lambda v:a.lerp(c,v)); right=right or (lambda v:b.lerp(d,v))
    def sample(u,v):
        return bottom(u)*(1-v)+top(u)*v+left(v)*(1-u)+right(v)*u-((1-u)*(1-v)*a+u*(1-v)*b+(1-u)*v*c+u*v*d)
    return sample

def finish(ob,direction,mirror=True,subdivision=2):
    me=ob.data; target=Vector(direction)
    if sum(poly.normal.dot(target) for poly in me.polygons)<0:
        bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    if mirror:
        m=ob.modifiers.new('Symmetry','MIRROR'); m.use_axis[0]=False; m.use_axis[1]=True; m.use_clip=True; m.merge_threshold=.0001
    if subdivision:
        m=ob.modifiers.new('Surface refinement','SUBSURF'); m.levels=1; m.render_levels=subdivision
    m=ob.modifiers.new('Panel thickness','SOLIDIFY'); m.thickness=.0025; m.offset=-1
    ob['construction']='Independent boundary-controlled quad patch; source semantic cage retained'
    return ob

def grid(name,sample,nu=12,nv=6,material=BODY,collection='03_BODY',normal=(0,0,1),mirror=True):
    # Support rows preserve panel boundaries and corners under SubD.
    def params(n): return [0,.012]+[i/n for i in range(1,n)]+[.988,1]
    us=params(nu); vs=params(nv); verts=[sample(u,v) for v in vs for u in us]; faces=[]
    for j in range(len(vs)-1):
        for i in range(len(us)-1):
            a=j*len(us)+i; faces.append((a,a+1,a+1+len(us),a+len(us)))
    ob=mesh(name,verts,faces,material,collection)
    ob['boundary_control']='Coons interpolation of authored semantic feature boundaries'
    ob['grid_us']=us; ob['grid_vs']=vs
    return finish(ob,normal,mirror)

# Hood boundaries derive directly from L01 and L02, including their offset nose.
hood_center=rail('L01_HOOD_CENTER',414,623)
hood_edge=rail('L02_HOOD_SHOULDER_R',425,623)
hood_front=authored([hood_center(0),p(415,.25,639),hood_edge(0)])
hood_back=authored([hood_center(1),p(623,.4,579),hood_edge(1)])
grid('HOOD',coons(hood_center,hood_edge,hood_front,hood_back),14,7,collection='04_PANELS')

# Front bridge between hood leading edge and bowed fascia.
nose_top=authored([p(402,0,646),p(408,.30,646),p(425,.60,640),p(448,.84,633)])
nose_lower=authored([p(398,0,705),p(402,.35,705),p(419,.60,708),p(437,.80,708)])
nose_crown=hood_front
grid('NOSE_HOOD_BRIDGE',coons(nose_top,nose_crown),12,4)
cheek_a=hood_edge(0); cheek_d=at_x('L02_HOOD_SHOULDER_R',sx(450)); cheek_c=at_x('L02_HOOD_SHOULDER_R',sx(470)); cheek_b=p(448,.84,633)
grid('NOSE_CHEEK',coons(authored([cheek_a,cheek_b]),authored([cheek_d,cheek_c]),rail('L02_HOOD_SHOULDER_R',425,450),authored([cheek_b,cheek_c])),7,6)
grid('BUMPER_FRONT',coons(nose_lower,nose_top,
    authored([nose_lower(0),p(395,0,673),nose_top(0)]),
    authored([nose_lower(1),p(437,.85,673),nose_top(1)])),14,8,normal=(-1,0,0))
lower_lip=authored([p(425,0,719),p(425,.35,719),p(433,.62,717),p(445,.84,716)])
grid('LIP_FRONT',coons(lower_lip,nose_lower),14,3,BLACK,normal=(-1,0,-1))

# Fender arch annuli. The inner border is an actual hole; outer controls are
# traced crown/quarter/rocker events, never a rectangular mesh with drawn arcs.
for axle,u,outer in [
 ('FRONT',520,[(437,.80,708),(433,.84,670),(446,.84,631),(479,.80,605),(520,.77,595),(570,.81,586),(623,.86,589),(611,.92,662),(598,.87,716)]),
 ('REAR',990,[(917,.87,716),(920,.92,665),(932,.91,620),(953,.87,580),(990,.85,579),(1042,.86,580),(1090,.86,596),(1110,.86,660),(1083,.80,710)])
]:
    # Ordered from front lower tangent, over crown, to rear lower tangent.
    angles=[math.radians(v) for v in (202,180,150,120,90,60,30,0,-22)]
    innerpts=[Vector((sx(u)+.465*math.cos(a),.89+.051*max(0,math.sin(a)),.406+.465*math.sin(a))) for a in angles]
    inner=authored(innerpts); out=authored([p(*q) for q in outer])
    # Both boundaries share angle-event parameterization, avoiding chord reordering.
    def indexed(pts):
        pts=list(map(Vector,pts))
        # Shape-preserving C1 tangents prevent Catmull overshoot at the cowl
        # and rear-quarter turn. Sparse geometric events remain authoritative.
        derivatives=[]
        for i,point in enumerate(pts):
            if i==0: tangent=pts[1]-pts[0]
            elif i==len(pts)-1:tangent=pts[-1]-pts[-2]
            else:
                before=pts[i]-pts[i-1]; after=pts[i+1]-pts[i]
                tangent=Vector(tuple(2*a*b/(a+b) if a*b>0 else 0 for a,b in zip(before,after)))
            derivatives.append(tangent)
        def sample(t):
            f=min(7.999999,max(0,t*8)); i=int(f); z=f-i
            return (2*z**3-3*z*z+1)*pts[i]+(z**3-2*z*z+z)*derivatives[i]+(-2*z**3+3*z*z)*pts[i+1]+(z**3-z*z)*derivatives[i+1]
        return sample
    inner=indexed(innerpts); out=indexed([p(*q) for q in outer])
    if axle=='FRONT':
        # One C1 boundary avoids tangent jumps between piecewise curve fragments.
        out=indexed([p(437,.80,708),p(437,.85,673),p(448,.84,633),at_x('L02_HOOD_SHOULDER_R',sx(470)),at_x('L02_HOOD_SHOULDER_R',sx(520)),at_x('L02_HOOD_SHOULDER_R',sx(580)),p(635,.86,589),p(611,.92,662),p(598,.87,716)])
    else:
        out=indexed([p(917,.87,716),p(920,.92,665),p(932,.91,620),p(954,.88,581),p(990,.85,579),p(1042,.86,580),p(1098,.80,579),p(1106,.86,650),p(1083,.80,710)])
    def rolled(a,r):
        f=inner(a); h=out(a); delta=h-f
        # Authored transverse tangent constraints: near-vertical at the arch
        # lip, turning into the hood/quarter crown at the outer boundary.
        c1=f+Vector((delta.x*.50,0,delta.z*.75))
        slope=.05
        if axle=='REAR':
            slopes=[0,.2,.6,.85,.6,.3,.05,0,0]; k=min(7,int(a*8)); z=min(1,a*8-k)
            slope=slopes[k]*(1-z)+slopes[k+1]*z
        c2=h+Vector((0,(f.y-h.y)*.65,-max(0,f.y-h.y)*.65*slope))
        return cubic(f,c1,c2,h,r)
    grid('FENDER_'+axle,rolled,24,8,normal=(0,1,0))
    lip=grid('ARCH_RETURN_'+axle,lambda a,r:inner(a)+Vector((0,-.028*r,0)),24,2,material=BLACK,normal=(0,1,0))
    # Physical recessed wheelhouse back and liner, visible through arch clearance.
    linerverts=[(sx(u),.65,.25)]+[(sx(u)+.464*math.cos(a),.65,.406+.464*math.sin(a)) for a in [math.radians(-22+i*224/48) for i in range(49)]]
    linerfaces=[(0,i+1,i+2) for i in range(48)]
    liner=mesh('WHEELHOUSE_'+axle,linerverts,linerfaces,BLACK,'03_BODY')
    finish(liner,(0,1,0),True,0)

# Door patch boundaries have independent front/rear edge curvature and a
# common shoulder/rocker rail. Separate objects create genuine panel structure.
for name,low,high,left,right in [
 ('DOOR_F',[(598,.87,716),(700,.88,716),(812,.88,716)],[(635,.86,589),(710,.87,586),(812,.87,583)],
  [(598,.87,716),(600,.92,665),(620,.90,610),(635,.86,589)],[(812,.88,716),(812,.92,677),(812,.926,613),(812,.87,583)]),
 ('DOOR_R',[(812,.88,716),(870,.88,716),(917,.87,716)],[(812,.87,583),(885,.88,582),(954,.88,581)],
  [(812,.88,716),(812,.92,677),(812,.926,613),(812,.87,583)],[(917,.87,716),(920,.92,665),(932,.91,620),(954,.88,581)])
]:
    ob=grid(name,coons(authored([p(*q) for q in low]),authored([p(*q) for q in high]),authored([p(*q) for q in left]),authored([p(*q) for q in right])),12,9,collection='04_PANELS',normal=(0,1,0))
    ob['panel_gap_m']=.003

# Cowl / sill ledge, between door shoulders and side glazing.
body_belt=authored([p(623,.86,589),p(800,.87,585),p(944,.88,581),p(1003,.86,579)])
glass_sill=rail('L10_WINDOW_SILL_R',633,1003)
grid('BELTLINE_LEDGE',coons(body_belt,glass_sill),20,3,normal=(0,1,1))

# Greenhouse is structurally independent. Center and side rails constrain
# all three upper glass patches; transverse crowns keep smooth roof flow.
for name,a,b in [('GLASS_WINDSHIELD',623,754),('GLASS_ROOF',754,943),('GLASS_REAR',943,1080)]:
    center=rail('L12_ROOF_CENTER',a,b)
    if a<943: edge=rail('L11_ROOF_EDGE_R',max(a,633),min(b,943))
    else: edge=authored([p(943,.62,545),p(1010,.60,562),p(1080,.62,581)])
    left=authored([center(0),(center(0)+edge(0))/2+Vector((0,0,.012)),edge(0)])
    right=authored([center(1),(center(1)+edge(1))/2+Vector((0,0,.012)),edge(1)])
    grid(name,coons(center,edge,left,right),12,8,GLASS,'05_GLASS')

# Side windows are separate curved patches with a real B-pillar gap.
for name,lower,upper,a,b in [
 ('GLASS_FRONT',[(652,.731,580),(703,.726,579),(758,.722,577),(801,.715,576)],[(652,.718,571),(699,.668,543),(757,.616,526),(801,.609,524)],633,812),
 ('GLASS_REAR_SIDE',[(822,.714,575),(875,.706,571),(931,.678,564),(997,.60,563)],[(822,.609,524),(875,.619,533),(928,.618,547),(997,.600,561)],812,1003)
]:
    lower_edge=authored([p(*q) for q in lower]); upper_edge=authored([p(*q) for q in upper])
    grid(name,coons(lower_edge,upper_edge),12,5,GLASS,'05_GLASS',normal=(0,1,0))
    frame_top=rail('L11_ROOF_EDGE_R',a,b); frame_bottom=rail('L10_WINDOW_SILL_R',a,b)
    grid('FRAME_TOP_'+name,coons(upper_edge,frame_top),12,2,normal=(0,1,1))
    grid('FRAME_BOTTOM_'+name,coons(frame_bottom,lower_edge),12,2,normal=(0,1,1))
    for label,t in [('FRONT',0),('BACK',1)]:
        pillar_material=BLACK if (name=='GLASS_FRONT' and label=='BACK') or (name=='GLASS_REAR_SIDE' and label=='FRONT') else BODY
        grid('FRAME_'+label+'_'+name,coons(authored([frame_bottom(t),lower_edge(t)]),authored([frame_top(t),upper_edge(t)])),2,6,pillar_material,normal=(0,1,0))

# Solid pillar / roof rail ribbons. They follow the semantic cage rather than
# being material strokes on the body or greenhouse.
edge=rail('L11_ROOF_EDGE_R',633,1003)
grid('ROOF_RAIL',lambda u,v:edge(u)+Vector((0,-.028*v,.005+v*.010)),24,2,normal=(0,1,1))
grid('PILLAR_B',coons(authored([p(801,.715,579),p(822,.714,578)]),authored([p(801,.61,520),p(822,.61,521)])),2,8,BLACK,normal=(0,1,0))

# Rear shoulder bridge to hatch glass, followed by a raised hatch lip.
grid('PILLAR_C_QUARTER',coons(authored([p(954,.88,581),p(990,.85,579),p(1042,.86,580),p(1098,.80,579)]),authored([p(943,.62,545),p(1010,.60,562),p(1080,.62,581)])),14,5)
hatch_top=authored([p(1080,0,580),p(1080,.35,580),p(1080,.62,581)])
hatch_lip=authored([p(1118,0,578),p(1118,.30,578),p(1111,.60,577),p(1098,.80,579)])
grid('REAR_HATCH_TOP',coons(hatch_top,hatch_lip),12,4,collection='04_PANELS')
hatch_bottom=authored([p(1126,0,647),p(1125,.35,647),p(1119,.65,649),p(1106,.86,650)])
grid('REAR_HATCH',coons(hatch_bottom,hatch_lip),14,8,collection='04_PANELS',normal=(1,0,0))
rear_low=authored([p(1120,0,711),p(1118,.35,711),p(1108,.65,710),p(1083,.80,710)])
grid('BUMPER_REAR',coons(rear_low,hatch_bottom,
    authored([rear_low(0),p(1128,0,674),hatch_bottom(0)]),
    authored([rear_low(1),p(1108,.86,678),hatch_bottom(1)])),14,7,normal=(1,0,0))

# Rocker volume is a distinct patch below the door skin, at the actual
# between-arch span. Openings remain physically clear.
grid('ROCKER',coons(authored([p(598,.84,719),p(760,.84,719),p(917,.84,719)]),authored([p(598,.88,699),p(760,.88,697),p(917,.88,697)])),20,3,BLACK,normal=(0,1,0))

# Revolved tire sidewall/tread profiles with genuine annular topology.
profile=[(.312,-.111),(.365,-.118),(.394,-.104),(.406,-.075),(.406,.075),(.394,.104),(.365,.118),(.312,.111)]
verts=[]; faces=[]; n=64
for r,y in profile:
    for i in range(n):
        a=i*math.tau/n; verts.append((r*math.cos(a),y,r*math.sin(a)))
for j in range(len(profile)):
    for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i))
base=None
for label,u,track,side in [('FL',520,1.61,-1),('FR',520,1.61,1),('RL',990,1.64,-1),('RR',990,1.64,1)]:
    if base is None: ob=mesh('WHEEL_'+label,verts,faces,TIRE,'07_WHEELS'); base=ob.data
    else:
        ob=bpy.data.objects.new('WHEEL_'+label,base); coll('07_WHEELS').objects.link(ob)
    ob.location=(sx(u),side*track/2,.406)
    ob['axle_source_px']=u
    capverts=[(0,side*.113,0)]+[(.313*math.cos(i*math.tau/64),side*.113,.313*math.sin(i*math.tau/64)) for i in range(64)]
    cap=mesh('WHEEL_BLOCKOUT_DISC_'+label,capverts,[(0,i+1,(i+1)%64+1) for i in range(64)],BLACK,'07_WHEELS')
    cap.location=ob.location

s=bpy.context.scene; s['model_status']='PATCH_BLOCKOUT_PENDING_SILHOUETTE_VALIDATION'
s['cage_status']='REVIEWED_SIDE_TOP_FRONT_OVERLAYS'; s['export_allowed']=False
s.render.engine='CYCLES'; s.cycles.samples=24
s.view_settings.view_transform='AgX'

# Studio lighting can be reused for every major validation milestone.
for ob in list(coll('09_PRESENTATION').objects):
    if ob.type=='LIGHT': bpy.data.objects.remove(ob,do_unlink=True)
for name,pos,power,size in [('KEY',(-3,-4,7),1600,5),('FILL',(1,4,5),1200,4),('RIM',(4,-1,6),1800,4)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    ob=bpy.data.objects.new(name,data); coll('09_PRESENTATION').objects.link(ob); ob.location=pos; aim(ob,(0,0,.7))
save()
for view,dims in [('side',(1200,560)),('top',(1200,600)),('front',(800,640)),('rear',(800,640)),('perspective',(1200,800))]:
    render('validation/'+view+'.png','CAM_3Q' if view=='perspective' else 'CAM_'+view.upper(),*dims)
print('PATCH_BLOCKOUT_CREATED: validation required before details or export')
