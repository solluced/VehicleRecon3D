import numpy as np
import pytest
from vehiclerecon.validation.silhouette import metrics,require,polygon_mask
from vehiclerecon.core.errors import GateError

def test_threshold_equality():
    r={'iou':.94,'threshold':.94,'status':'PASS'}
    require({'side':r})

def test_threshold_failure():
    with pytest.raises(GateError):require({'side':{'iou':.9399,'threshold':.94,'status':'FAIL'}})

def test_large_regression():
    with pytest.raises(GateError):require({'side':{'iou':.945,'threshold':.94,'status':'PASS'}},{'side':.95723},.002)

def test_masks():
    mask=polygon_mask([(0,0),(2,0),(2,2),(0,2)],3,3)
    assert mask.sum()==4
    assert metrics(mask,mask,1)['status']=='PASS'
    assert metrics(mask,mask,1)['iou']==1
