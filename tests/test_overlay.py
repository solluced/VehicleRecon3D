import numpy as np
from vehiclerecon.reference.overlay_extract import extract,components,hsv

def test_color_proposals():
    import json
    rgb=np.zeros((12,12,3));rgb[1:3,1:3]=(1,.5,0);rgb[4:6,1:3]=(0,0,1);rgb[7:9,1:3]=(1,0,0);rgb[1:3,7:9]=(0,1,0)
    result=extract(rgb)
    assert json.loads(json.dumps(result))['schema_version']==1
    assert result['status']=='PROPOSAL_NOT_SEMANTIC_GEOMETRY'
    for color in ['orange','blue','red','green']:
        assert result['colors'][color]['mask_pixels']==4
        assert len(result['colors'][color]['components'])==1

def test_eight_connected():
    mask=np.eye(4,dtype=bool)
    result=components(mask)
    assert len(result)==1 and result[0]['pixels']==4
    assert result[0]['centroid_px']==[1.5,1.5]
