"""Fixed-camera mask metrics and required acceptance errors."""
import numpy as np
from ..core.errors import GateError

def polygon_mask(points,width,height):
    yy,xx=np.mgrid[0:height,0:width];xx=xx+.5;yy=yy+.5
    inside=np.zeros((height,width),dtype=bool)
    for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
        if abs(by-ay)<1e-10:continue
        inside^=((ay>yy)!=(by>yy))&(xx<(bx-ax)*(yy-ay)/(by-ay)+ax)
    return inside

def bbox(mask):
    yy,xx=np.where(mask)
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None

def metrics(reference,model,threshold):
    intersection=np.count_nonzero(reference&model);union=np.count_nonzero(reference|model)
    iou=intersection/union if union else 0
    mismatch=np.count_nonzero(reference^model);rb=bbox(reference);mb=bbox(model)
    return {'status':'PASS' if iou>=threshold else 'FAIL','iou':round(iou,6),'threshold':threshold,
            'pixel_mismatch_percent_of_frame':round(100*mismatch/reference.size,4),
            'pixel_mismatch_percent_of_union':round(100*mismatch/max(1,union),4),
            'reference_bbox_px':rb,'model_bbox_px':mb,
            'bbox_difference_px':[b-a for a,b in zip(rb,mb)] if rb and mb else None,
            'render_size':[model.shape[1],model.shape[0]]}

def require(results,baseline=None,max_regression=0):
    for view,result in results.items():
        if result['status']!='PASS':
            raise GateError(f"Silhouette {view} IoU {result['iou']} < {result['threshold']}")
        if baseline and result['iou'] < baseline[view]-max_regression:
            raise GateError(f'Silhouette {view} regressed beyond configured allowance')
