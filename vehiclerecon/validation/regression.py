"""Functional fixture comparison; diagnostic topology overlays are reported separately."""
from ..core.errors import GateError

def compare_sources(expected,actual,overlay_names,tolerance):
    if set(expected)!=set(actual):raise GateError('Regression changed exported object identities')
    physical=[];overlays=[]
    for name,source in expected.items():
        current=actual[name]
        error=max(abs(a-b) for key in ('bounds_min','bounds_max') for a,b in zip(source[key],current[key]))
        entry={'object':name,'max_bounds_delta_m':error,'baseline_triangles':source['triangles'],'current_triangles':current['triangles']}
        (overlays if name in overlay_names else physical).append(entry)
    failed=[r for r in physical if r['max_bounds_delta_m']>tolerance or r['baseline_triangles']!=r['current_triangles']]
    report={'status':'FAIL' if failed else 'PASS','physical_objects':physical,'topology_overlays':overlays,
            'max_physical_bounds_delta_m':max((r['max_bounds_delta_m'] for r in physical),default=0),
            'max_overlay_bounds_delta_m':max((r['max_bounds_delta_m'] for r in overlays),default=0),
            'physical_failures':failed,
            'policy':'Vehicle surfaces/details retain source bounds and triangle counts. Diagnostic mesh-edge overlays are compared and reported separately; each current exported overlay still must pass direct Blender-to-GLB verification.'}
    return report
