"""Inspectable content cache: a hit verifies every recorded output byte."""
import re
from .project import read_json,REPOSITORY,RESOURCE_ROOT
from .manifest import digest_file,digest_data,write_json
from .errors import SchemaError,ReferenceError

def implementation_hash():
    roots={'package':REPOSITORY/'vehiclerecon','schemas':RESOURCE_ROOT/'schemas','profiles':RESOURCE_ROOT/'profiles'}
    files={label+'/'+p.relative_to(root).as_posix():digest_file(p) for label,root in roots.items()
           for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in ('.py','.html','.mjs','.json') and '__pycache__' not in p.parts}
    return digest_data(files)

class StageCache:
    def __init__(self,project,implementation=None):
        self.project=project
        self.implementation=implementation or implementation_hash()

    def path(self,stage):
        if not re.fullmatch('[a-z_]+',stage):raise SchemaError('Invalid cache stage name')
        return self.project.path('.cache/'+stage+'.json')

    def key(self,stage,inputs,dependencies):
        return digest_data({'schema_version':1,'stage':stage,'implementation':self.implementation,
                            'inputs':inputs,'dependencies':dependencies})

    def hit(self,stage,key):
        try:
            entry=read_json(self.path(stage))
            if entry.get('schema_version')!=1 or entry.get('stage')!=stage or entry.get('status')!='PASS' or entry.get('key')!=key:return None
            for item in entry['outputs']:
                path=self.project.path(item['path'],exists=True)
                if digest_file(path)!=item['sha256']:return None
            if entry['result_key']!=digest_data({'key':key,'outputs':entry['outputs']}):return None
            return entry
        except (SchemaError,ReferenceError,OSError,KeyError,ValueError):
            return None

    def store(self,stage,key,outputs,dependencies,inputs,status='PASS',message=''):
        items=[]
        if status=='PASS':
            for relative in sorted(set(outputs)):
                path=self.project.path(relative,exists=True)
                items.append({'path':relative,'sha256':digest_file(path)})
        entry={'schema_version':1,'stage':stage,'status':status,'key':key,'implementation':self.implementation,
               'inputs':inputs,'dependency_keys':dependencies,'outputs':items,'message':message,
               'result_key':digest_data({'key':key,'outputs':items})}
        temporary=self.path(stage).with_suffix('.json.tmp')
        write_json(temporary,entry);temporary.replace(self.path(stage))
        return entry

def input_slice(project,stage,*,include_review=True):
    d=project.data
    def generated(name):
        path=d['generated'][name]
        return {'path':path,'sha256':digest_file(project.path(path,exists=True))}
    def validation():
        return {k:d['validation'][k] for k in ('thresholds','baseline_iou','max_iou_regression')}
    if stage=='preflight':return {'metadata':{k:d[k] for k in ('schema_version','project_id','category','vehicle_profile','asset_name')},'profile':project.profile}
    if stage=='references':return {k:{'path':v,'sha256':digest_file(project.path(v,exists=True))} for k,v in d['references'].items()}
    if stage=='calibration':return {'calibration':generated('calibration'),'scene':d['scene'],'materials':d['materials'],'dimensions':d['dimensions']}
    if stage=='overlay':return {'annotation_convention':'orange-blue-red-green-v1'}
    if stage=='cage':return {'cage':generated('cage')}
    if stage=='surfaces':
        result={'graph':generated('surface_graph')}
        if d['schema_version']==2:
            result['authoring_reviews']={kind:digest_file(project.path('validation/'+kind+'_review.json',exists=True)) for kind in ('source','cage')}
        return result
    if stage=='silhouette':return {'traces':generated('silhouette_traces'),'validation':validation(),'mask_exclusions':d['export']['excluded_collections'],'views':[v for v in d['presentation']['views'] if v['view']!='perspective']}
    if stage=='details':return {'details':generated('details')}
    if stage=='geometry':return {'policy':d['validation']['geometry'],'roles':d['roles'],'model_collections':d['export']['collections']}
    if stage=='presentation':
        result={'presentation':d['presentation'],'validation':validation()}
        if include_review:
            path=project.path('validation/review.json')
            result['review_sha256']=digest_file(path) if path.is_file() else None
        return result
    if stage=='export':return d['export']
    if stage=='glb_verify':return {'bounds_tolerance_m':d['validation']['bounds_tolerance_m']}
    if stage=='viewer':return d['viewer']
    if stage=='delivery':return {'project_id':d['project_id'],'asset_name':d['asset_name']}
    raise SchemaError(f'Unknown cache slice {stage}')
