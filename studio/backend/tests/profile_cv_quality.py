"""Reproducible 4K local baseline quality/timing probe; no canonical writes."""
import json,sys,time
from pathlib import Path
import cv2 as cv
import numpy as np
from prepare_cv import prepare
from vehiclerecon.core.manifest import digest_file
from vehiclerecon_studio.cv.providers import OpenCVProvider
from vehiclerecon_studio.cv.cache import ByteCache
from vehiclerecon_studio.cv import opencv
repo=Path(__file__).resolve().parents[3];root=repo/f'build/studio03-quality-{time.time_ns()}/projects'
prepare(root);path=root/'cv_performance/input/reference.png';raw=path.read_bytes();cache=ByteCache()
ctx={'source_hash':digest_file(path),'crop':[0,0,3840,2160],'cache':cache,'check':lambda:None}
original=opencv._contours;extractions=[]
def measured(*a,**kw):
    start=time.perf_counter()
    try:return original(*a,**kw)
    finally:extractions.append((time.perf_counter()-start)*1000)
opencv._contours=measured
provider=OpenCVProvider();roi=[1200,600,3330,1680];start=time.perf_counter()
first=provider.run('segment_object',raw,{'roi':roi},ctx);first_ms=(time.perf_counter()-start)*1000
image=cv.imdecode(np.frombuffer(raw,np.uint8),cv.IMREAD_COLOR)[600:1680,1200:3330]
truth=np.any(image!=np.array([246,245,244]),axis=2)
actual=cv.imdecode(np.frombuffer(first['rasters']['mask'],np.uint8),cv.IMREAD_UNCHANGED)[:,:,3]>0
iou=float(np.count_nonzero(actual&truth)/np.count_nonzero(actual|truth))
if iou<.99:raise RuntimeError(f'Analytical mask IoU {iou}')
times=[]
for label,point in [('foreground',[2000,1000]),('background',[2100,1200])]:
    start=time.perf_counter();refined=provider.run('segment_object',raw,{'roi':roi,
        'strokes':[{'label':label,'points':[point],'radius':16}]},ctx);times.append((time.perf_counter()-start)*1000)
    if not refined['components']:raise RuntimeError('No refined contour')
result={'status':'PASS','source':[3840,2160],'roi':roi,'provider':provider.metadata(),'opencv_runtime':cv.__version__,
    'first_mask_ms':first_ms,'refinement_ms':times,'contour_extraction_and_bounded_fitting_ms':extractions,
    'mask_pixel_iou_against_analytic_foreground':iou,'foreground_pixels':first['mask']['foreground_pixels'],
    'contour_count':len(first['components']),'fit_reports':[c['fit'] for c in first['components']],
    'retained_field_data_bytes':cache.bytes,'note':'CPU-only synthetic analytic fixture. Timings include local decoding on first request; contour extraction includes pure-core bounded fitting. Pixel IoU is fixture-specific, not vehicle recognition accuracy.'}
(repo/'build/studio03-cv-quality.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
