"""Render the five fixed calibrated views of the current Blender model."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project import *
s=bpy.context.scene; s.render.engine='CYCLES'; s.cycles.samples=32; s.view_settings.view_transform='AgX'
for col in ('00_REFERENCE','01_CURVE_CAGE'):
    for ob in coll(col).objects: ob.hide_render=True
for view,w,h in [('side',1200,560),('top',1200,600),('front',800,640),('rear',800,640),('perspective',1200,800)]:
    render('validation/'+view+'.png','CAM_3Q' if view=='perspective' else 'CAM_'+view.upper(),w,h)
