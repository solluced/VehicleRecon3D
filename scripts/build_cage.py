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
for ob in list(coll('01_CURVE_CAGE').objects): bpy.data.objects.remove(ob,do_unlink=True)

# Coordinates are (side-sheet u, physical half-width, side-sheet v).
RAILS={
 'L00_CENTERLINE':[(395,0,741),(520,0,741),(990,0,741),(1128,0,741)],
 'L01_HOOD_CENTER':[(414,0,639),(450,0,617),(514,0,596),(578,0,582),(623,0,577)],
 'L02_HOOD_SHOULDER':[(414,.53,637),(458,.70,615),(520,.77,595),(580,.78,584),(623,.78,582)],
 'L03_FRONT_FENDER_CROWN':[(403,.61,638),(450,.85,615),(520,.94,607),(580,.92,599),(625,.86,589)],
 'L04_UPPER_ARCH_TRANSITION':[(445,.90,647),(466,.94,621),(520,.941,610),(574,.94,624),(597,.90,652)],
 'L05_BELT':[(403,.70,650),(451,.91,626),(520,.94,614),(600,.90,598),(635,.86,589),(800,.87,585),(944,.88,581),(1048,.91,579),(1118,.80,584)],
 'L06_SHOULDER_CHARACTER':[(402,.77,654),(451,.91,642),(591,.92,626),(760,.926,613),(919,.93,601),(1060,.93,599),(1120,.84,604)],
 'L07_DOOR_LOWER_CHARACTER':[(596,.91,692),(690,.915,681),(801,.918,670),(898,.91,662),(924,.91,665)],
 'L08_ROCKER_UPPER':[(435,.78,701),(597,.88,699),(760,.88,697),(917,.88,697),(1090,.83,699)],
 'L09_ROCKER_LOWER':[(430,.76,713),(598,.87,716),(760,.87,716),(917,.87,716),(1090,.80,712)],
 'L10_WINDOW_SILL':[(633,.82,584),(760,.81,581),(866,.80,575),(954,.75,564),(1003,.65,550)],
 'L11_ROOF_EDGE':[(633,.82,579),(697,.75,540),(758,.71,521),(815,.70,519),(870,.70,526),(933,.68,542),(1003,.65,550)],
 'L12_ROOF_CENTER':[(623,0,577),(688,0,536),(754,0,513),(813,0,508),(873,0,515),(943,0,535),(1010,0,558),(1090,0,580)],
 'L13_REAR_QUARTER_SHOULDER':[(933,.88,579),(990,.94,584),(1050,.93,582),(1118,.80,580)],
 'L14_HATCH_TRANSITION':[(1003,.65,550),(1046,.71,564),(1090,.72,577),(1118,.67,570)],
 'L15_LOWER_BUMPER':[(398,.74,691),(414,.82,702),(437,.83,707)],
 'L15_REAR_LOWER_BUMPER':[(1083,.84,707),(1110,.82,695),(1125,.74,674)]
}
for name,pts in RAILS.items():
    if all(y==0 for u,y,v in pts): curve('CAGE_'+name,[p(*a) for a in pts],BLUE,.003)
    else:
        for side,sgn in [('L',-1),('R',1)]:
            curve('CAGE_'+name+'_'+side,[p(u,y*sgn,v) for u,y,v in pts],BLUE,.003)

# Hand-authored half-sections at feature events. Each is independent: not
# evenly spaced sections for an automatic outer-profile loft.
SECTIONS=[
 ('T00_FRONT_BUMPER',398,[(0,663),(.50,662),(.74,654),(.82,669),(.80,694),(.63,703),(0,705)]),
 ('T01_FRONT_LAMP',425,[(0,630),(.53,633),(.76,636),(.87,647),(.87,675),(.80,704),(0,708)]),
 ('T02_HOOD_FRONT',457,[(0,614),(.55,616),(.79,620),(.91,633),(.91,665),(.83,710),(0,713)]),
 ('T03_FRONT_WHEEL',520,[(0,595),(.58,595),(.77,598),(.94,610)]),
 ('T04_REAR_FRONT_WHEEL',597,[(0,581),(.56,582),(.79,587),(.89,600),(.92,645),(.88,699),(.87,716),(0,716)]),
 ('T05_A_PILLAR',665,[(0,550),(.50,554),(.78,560),(.84,584),(.91,623),(.91,675),(.87,716),(0,716)]),
 ('T06_FRONT_SEAT',735,[(0,518),(.47,522),(.72,531),(.81,582),(.925,617),(.92,676),(.87,716),(0,716)]),
 ('T07_B_PILLAR',812,[(0,508),(.47,512),(.70,519),(.81,578),(.926,609),(.92,678),(.87,716),(0,716)]),
 ('T08_REAR_DOOR',900,[(0,521),(.47,525),(.70,534),(.79,571),(.93,602),(.915,677),(.87,716),(0,716)]),
 ('T09_C_PILLAR',954,[(0,539),(.45,541),(.67,547),(.75,564),(.91,594)]),
 ('T10_REAR_WHEEL',990,[(0,552),(.45,554),(.66,554),(.86,582),(.94,611)]),
 ('T11_REAR_QUARTER',1055,[(0,573),(.45,574),(.73,573),(.92,590),(.93,642),(.84,706),(0,714)]),
 ('T12_REAR_LAMP',1110,[(0,581),(.44,580),(.72,576),(.84,588),(.88,625),(.83,687),(.70,706),(0,714)]),
 ('T13_REAR_BUMPER',1125,[(0,604),(.45,603),(.72,605),(.83,625),(.83,665),(.76,689),(0,707)])
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
        arch=[(center+.465*math.cos(a),sgn*.943,.406+.465*math.sin(a)) for a in [math.radians(x) for x in (-22,0,35,70,90,110,145,180,202)]]
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
