"""Reproducible release workload: private 27-patch project, 100 edits, real CV cache."""
import copy
import gc
import hashlib
import io
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_surfaces import prepare
from vehiclerecon.core.project import REPOSITORY
from vehiclerecon.authoring.workspace import Workspace
from vehiclerecon.authoring.service import AuthoringSession
from vehiclerecon.surfaces.preview import evaluate
from vehiclerecon_studio.workspace import Registry
from vehiclerecon_studio.security import Config


def rss(peak=False):
    return int(subprocess.check_output([sys.executable,str(Path(__file__).with_name('process_memory.py')),str(os.getpid()),*(['--peak'] if peak else [])]))


def timed(fn):
    start=time.perf_counter();value=fn();return value,(time.perf_counter()-start)*1000


def summary(values):
    ordered=sorted(values)
    return {'samples':len(values),'p50_ms':statistics.median(values),'p95_ms':ordered[min(len(ordered)-1,int(len(ordered)*.95))],'values_ms':values}


def main():
    target=REPOSITORY/'build'/('studio05-surface-retention-'+str(time.time_ns()))/'projects'
    prepare(target);registry=Registry(Config((target,),9173));path=target/'dense';cache=registry.surface_cache
    session=AuthoringSession(path,history_limit=100,history_byte_limit=32*1024*1024)
    def apply(command):return session.apply([command],expected_revision=session.revision)
    gc.collect();baseline=rss();samples=[{'edits':0,'rss_bytes':baseline}]
    initial,first=timed(lambda:evaluate(Workspace(path),quality='medium',cache=cache))
    if initial['status']!='PASS':raise RuntimeError(initial['validation'])
    # Build a real decoded source / Canny / gradient field through the trusted CV provider.
    image=Image.new('RGB',(512,512),'#dce5e7');draw=ImageDraw.Draw(image);draw.rectangle((50,100,460,430),outline='#334455',width=5)
    raw=io.BytesIO();image.save(raw,format='PNG');raw=raw.getvalue();source_hash=hashlib.sha256(raw).hexdigest()
    edits=[];previews=[];last=None
    for i in range(100):
        points=[[0,0,i*.00001],[1,0,i*.00001],[1,1,i*.00001],[0,1,i*.00001]]
        _,elapsed=timed(lambda:apply(dict(type='SetSurfaceParameter',node_id='grid.sample.0',parameter='points',value=points)))
        edits.append(elapsed);last,elapsed=timed(lambda:evaluate(Workspace(path),quality='medium',cache=cache));previews.append(elapsed)
        if last['status']!='PASS':raise RuntimeError(last['validation'])
        if i and last['sampled_patches']!=['grid.panel.0']:raise RuntimeError('Incremental evaluator sampled an unrelated patch')
        result=registry.cv.providers.run('opencv','detect_edges',raw,{'threshold':50+i},{'source_hash':source_hash,'crop':[0,0,512,512],'cache':registry.cv.fields,'check':lambda:None})
        registry.cv.results.put(('benchmark',i),result)
        if (i+1)%10==0:
            gc.collect();samples.append({'edits':i+1,'rss_bytes':rss(),'surface_cache':cache.metrics(),'history_payload_bytes':session.history_retained_bytes,'cv':registry.cv.metrics()})
    peak=rss(True);gc.collect();post=rss()
    before_undo=(path/'generated/surface_graph.json').read_bytes();session.undo(expected_revision=session.revision);session.redo(expected_revision=session.revision)
    if (path/'generated/surface_graph.json').read_bytes()!=before_undo:raise RuntimeError('Undo/redo changed exact bytes')
    # Distinct command categories; never compare these small source edits with the 5,000-point browser workload.
    source=AuthoringSession(target/'rejected');start=time.perf_counter();source.apply([dict(type='MoveObservation',observation_id='obs_roof_side',pixel=[129,78])],expected_revision=source.revision);source_edit=(time.perf_counter()-start)*1000
    _,creation=timed(lambda:apply(dict(type='AddSurfacePatch',patch_id='benchmark.draft',node_id='benchmark.sample',name='Draft',semantic_role='panel',op='coons')))
    report={'status':'PASS','workload':{'patches':27,'operations':['coons','bilinear_patch'],'preview_quality':'medium','canonical_surface_edits':100,'cv_source_size':[512,512],'cv_generations':100},
        'first_core_preview_ms':first,'surface_parameter_edit':summary(edits),'incremental_preview':summary(previews),
        'draft_patch_creation_ms':creation,'small_source_edit_ms':source_edit,'source_edit_comparison':'Separate small analytic edit; dense 4K/5000/20-layer baseline measured by browser performance suite.',
        'rss_bytes':{'baseline':baseline,'peak':peak,'post_gc':post},'samples':samples,
        'preview_payload_bytes':len(json.dumps(last,allow_nan=False).encode()),'history_payload_bytes':session.history_retained_bytes,
        'cache':cache.metrics(),'cv':registry.cv.metrics(),'retention':'Surface node LRU 256 entries; mesh LRU 64 entries/16MiB; history 100 edges/32MiB; existing CV byte limits.',
        'undo_redo_exact':True}
    (REPOSITORY/'build/studio05-surface-retention.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','first_core_preview_ms','draft_patch_creation_ms','rss_bytes','preview_payload_bytes','history_payload_bytes')},indent=2));registry.cv.close()


if __name__=='__main__':main()
