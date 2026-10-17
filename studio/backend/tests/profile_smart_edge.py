"""Before/after identical local Smart Edge work; baseline is a trusted local release module."""
import argparse,cProfile,importlib.util,json,pstats,sys,time,hashlib
from pathlib import Path
from prepare_cv import prepare
from vehiclerecon_studio.cv import opencv
from vehiclerecon_studio.cv.cache import ByteCache
from vehiclerecon.core.manifest import digest_file
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline-module',type=Path,required=True)
args=parser.parse_args();repo=Path(__file__).resolve().parents[3]
path=args.baseline_module.resolve(strict=True)
if not path.is_relative_to(repo/'build') or path.name!='opencv.py':parser.error('Use the trusted locally installed v0.3 wheel module under build/')
spec=importlib.util.spec_from_file_location('release_baseline_opencv',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
root=repo/f'build/studio04-smart-profile-{time.time_ns()}/projects';prepare(root)
source=root/'cv_performance/input/reference.png';raw=source.read_bytes();outputs={};profiles={};timings={}
for label,module in [('v03',old),('v04',opencv)]:
    cache=ByteCache();ctx={'source_hash':digest_file(source),'crop':[0,0,3840,2160],'cache':cache,'check':lambda:None}
    values=[];results=[]
    for i in range(7):
        began=time.perf_counter();r=module.run('smart_edge',raw,{'trajectory':[[500,500],[500,600],[500,700],[500,800]],'search_radius':24},ctx)
        values.append((time.perf_counter()-began)*1000);results.append(r)
    prof=cProfile.Profile();prof.enable();module.run('smart_edge',raw,{'trajectory':[[500,500],[500,600],[500,700],[500,800]],'search_radius':24},ctx);prof.disable()
    stats=pstats.Stats(prof);phases={}
    for name,predicate in {'image_decode':lambda n:'imdecode' in n,'edge_lookup':lambda n:n=='_field',
        'path_search_inclusive_fit':lambda n:n=='_smart','core_contour_fit':lambda n:n=='_component',
        'constant_direction_dot':lambda n:'dot' in n}.items():
        entries=[v for (f,line,n),v in stats.stats.items() if predicate(n)]
        phases[name]={'calls':sum(v[1] for v in entries),'self_seconds':sum(v[2] for v in entries),'cumulative_seconds':sum(v[3] for v in entries)}
    outputs[label]=results;timings[label]={'cold_ms':values[0],'warm_ms':values[1:],'warm_p50_ms':sorted(values[1:])[3],'warm_p95_ms':max(values[1:])};profiles[label]=phases
if outputs['v03']!=outputs['v04']:raise RuntimeError('Smart Edge result changed')
report={'status':'PASS','source':[3840,2160],'baseline_module_sha256':digest_file(path),'exact_result_equivalence':True,
    'timings':timings,'profile_phases':profiles,'debounce_ms':80,'poll_interval_ms':20,
    'note':'Identical directed 300px segment; cold includes decode. Warm profile excludes decode, includes cached edge lookup, path search and pure-core contour fitting. Browser benchmark separately includes HTTP/poll and two animation frames.'}
(repo/'build/studio04-smart-edge-profile.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
