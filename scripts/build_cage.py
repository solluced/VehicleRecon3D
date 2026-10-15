"""Authored semantic feature curves, traced from the primary multiview.

This builds a sparse curve network, never a body loft. Side u/v landmarks
define longitudinal and vertical placement; lateral controls come from top
and rectified end views. Every control is a named geometric event.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *

def p(u,y,v): return (sx(u),y,sz(v))
BLUE=emissive('MAT_CAGE_BLUE',(.015,.14,.65))
CYAN=emissive('MAT_CAGE_SECTION',(.04,.42,.66))
for col in ('02_BLOCKOUT','03_BODY','04_PANELS','05_GLASS','06_LIGHTS','07_WHEELS','08_INTERIOR'):
    for ob in coll(col).objects: ob.hide_render=True
for ob in list(coll('01_CURVE_CAGE').objects): bpy.data.objects.remove(ob,do_unlink=True)

# Coordinates are (side-sheet u, physical half-width, side-sheet v).
RAILS={
 'L00_CENTERLINE':[(395,0,741),(520,0,741),(990,0,741),(1128,0,741)],
 'L01_HOOD_CENTER':[(414,0,639),(450,0,617),(514,0,596),(578,0,582),(623,0,577)],
 'L02_HOOD_SHOULDER':[(425,.53,637),(458,.70,615),(520,.77,595),(580,.78,584),(623,.78,582)],
 'L03_FRONT_FENDER_CROWN':[(425,.61,638),(450,.83,615),(520,.94,607),(580,.92,599),(625,.86,589)],
 'L04_UPPER_ARCH_TRANSITION':[(445,.90,647),(466,.94,621),(520,.941,610),(574,.94,624),(597,.90,652)],
 'L05_BELT':[(425,.60,650),(451,.84,626),(520,.94,614),(600,.90,598),(635,.86,589),(800,.87,585),(944,.88,581),(1048,.91,579),(1118,.58,584)],
 'L06_SHOULDER_CHARACTER':[(427,.65,654),(451,.85,642),(591,.92,626),(760,.926,613),(919,.93,601),(1060,.93,599),(1120,.55,604)],
 'L07_DOOR_LOWER_CHARACTER':[(596,.91,692),(690,.915,681),(801,.918,670),(898,.91,662),(924,.91,665)],
 'L08_ROCKER_UPPER':[(435,.78,701),(597,.88,699),(760,.88,697),(917,.88,697),(1090,.83,699)],
 'L09_ROCKER_LOWER':[(430,.76,713),(598,.87,716),(760,.87,716),(917,.87,716),(1090,.80,712)],
 'L10_WINDOW_SILL':[(633,.74,584),(760,.73,581),(866,.72,575),(954,.675,564),(1003,.60,562)],
 'L11_ROOF_EDGE':[(633,.74,579),(697,.67,540),(758,.62,521),(815,.61,519),(870,.62,526),(933,.62,542),(1003,.60,562)],
 'L12_ROOF_CENTER':[(623,0,577),(688,0,536),(754,0,513),(813,0,508),(873,0,515),(943,0,535),(1010,0,558),(1090,0,580)],
 'L13_REAR_QUARTER_SHOULDER':[(933,.88,579),(990,.94,584),(1050,.93,582),(1118,.58,580)],
 'L14_HATCH_TRANSITION':[(1003,.60,562),(1046,.62,575),(1090,.70,579),(1118,.48,578)],
 'L15_LOWER_BUMPER':[(398,.20,691),(414,.49,702),(437,.73,707)],
 'L15_REAR_LOWER_BUMPER':[(1083,.84,707),(1110,.70,695),(1125,.34,674)]
}
for name,pts in RAILS.items():
    if all(y==0 for u,y,v in pts): curve('CAGE_'+name,[p(*a) for a in pts],BLUE,.003)
    else:
        for side,sgn in [('L',-1),('R',1)]:
            curve('CAGE_'+name+'_'+side,[p(u,y*sgn,v) for u,y,v in pts],BLUE,.003)

# Hand-authored half-sections at feature events. Each is independent: not
# evenly spaced sections for an automatic outer-profile loft.
SECTIONS=[
 ('T00_FRONT_BUMPER',398,[(0,663),(.12,662),(.22,654),(.28,669),(.25,694),(.18,703),(0,705)]),
 ('T01_FRONT_LAMP',425,[(0,630),(.43,633),(.58,636),(.65,647),(.65,675),(.60,704),(0,708)]),
 ('T02_HOOD_FRONT',457,[(0,614),(.55,616),(.76,620),(.87,633),(.87,665),(.80,710),(0,713)]),
 ('T03_FRONT_WHEEL',520,[(0,595),(.58,595),(.77,598),(.94,610)]),
 ('T04_REAR_FRONT_WHEEL',597,[(0,581),(.56,582),(.79,587),(.89,600),(.92,645),(.88,699),(.87,716),(0,716)]),
 ('T05_A_PILLAR',665,[(0,550),(.50,554),(.70,560),(.75,584),(.91,623),(.91,675),(.87,716),(0,716)]),
 ('T06_FRONT_SEAT',735,[(0,518),(.47,522),(.63,531),(.73,582),(.925,617),(.92,676),(.87,716),(0,716)]),
 ('T07_B_PILLAR',812,[(0,508),(.47,512),(.61,519),(.73,578),(.926,609),(.92,678),(.87,716),(0,716)]),
 ('T08_REAR_DOOR',900,[(0,521),(.47,525),(.62,534),(.71,571),(.93,602),(.915,677),(.87,716),(0,716)]),
 ('T09_C_PILLAR',954,[(0,539),(.45,541),(.615,547),(.675,564),(.91,594)]),
 ('T10_REAR_WHEEL',990,[(0,552),(.45,554),(.60,560),(.86,582),(.94,611)]),
 ('T11_REAR_QUARTER',1055,[(0,573),(.45,574),(.73,573),(.92,590),(.93,642),(.84,706),(0,714)]),
 ('T12_REAR_LAMP',1110,[(0,581),(.30,580),(.55,576),(.68,588),(.72,625),(.65,687),(.52,706),(0,714)]),
 ('T13_REAR_BUMPER',1125,[(0,604),(.18,603),(.30,605),(.40,625),(.40,665),(.30,689),(0,707)])
]
for name,u,half in SECTIONS:
    pts=[p(u,-y,v) for y,v in reversed(half[1:])]+[p(u,y,v) for y,v in half]
    curve('CAGE_'+name,pts,CYAN,.0022)

for axle,u,track in [('FRONT',520,1.61),('REAR',990,1.64)]:
    for side,sgn in [('L',-1),('R',1)]:
        # True circular tire datum; arch controls are independent of this circle.
        center=sx(u)
        points=[(center+.406*math.cos(a),sgn*track/2,.406+.406*math.sin(a)) for a in [i*math.tau/12 for i in range(12)]]
        curve('CAGE_WHEEL_'+axle+'_'+side,points,CYAN,.0025,cyclic=True)
        arch=[(center+.465*math.cos(a),sgn*(.89+.051*max(0,math.sin(a))),.406+.465*math.sin(a)) for a in [math.radians(x) for x in (-22,0,35,70,90,110,145,180,202)]]
        curve('CAGE_ARCH_'+axle+'_'+side,arch,BLUE,.004)

bpy.context.scene['cage_status']='SEMANTIC_NETWORK_CREATED_PENDING_OVERLAY_REVIEW'
bpy.context.scene['model_status']='CURVE_CAGE_ONLY_NO_BODY'
save()
for view,dims in [('side',(1200,560)),('top',(1200,600)),('front',(800,640)),('rear',(800,640)),('perspective',(1200,800))]:
    cam='CAM_3Q' if view=='perspective' else 'CAM_'+view.upper()
    render('validation/cage_'+view+'.png',cam,*dims)
    if view!='perspective':
        ref=bpy.data.objects['REF_'+view.upper()]; ref.hide_render=False
        render('validation/cage_overlay_'+view+'.png',cam,*dims)
        ref.hide_render=True
print('CAGE_CREATED',len(coll('01_CURVE_CAGE').objects),'semantic curves; no surfaces')
