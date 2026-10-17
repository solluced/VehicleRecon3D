"""CLI evolves with the implemented migration phases."""
import argparse
import json
from .core.errors import ReconError
from .core.project import Project

def main(argv=None):
    parser = argparse.ArgumentParser(prog='vehicle-recon')
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('project')
    studio=commands.add_parser('studio');studio.add_argument('--root',action='append',default=[]);studio.add_argument('--port',type=int,default=0);studio.add_argument('--host',default='127.0.0.1');studio.add_argument('--no-browser',action='store_true')
    init=commands.add_parser('init');init.add_argument('project');init.add_argument('--profile',default='sedan');init.add_argument('--schema-version',type=int,choices=[1,2],default=1)
    migration=commands.add_parser('migrate');migration.add_argument('project');migration.add_argument('--to',type=int,required=True);migration.add_argument('--dry-run',action='store_true');migration.add_argument('--expected-revision')
    authoring=commands.add_parser('authoring-status');authoring.add_argument('project')
    run=commands.add_parser('run');run.add_argument('project');run.add_argument('--blender');run.add_argument('--no-cache',action='store_true');run.add_argument('--until',choices=['preflight','references','calibration','overlay','cage','surfaces','silhouette','details','geometry','presentation','export','glb_verify','viewer','delivery'])
    review=commands.add_parser('review');review.add_argument('project');review.add_argument('--reviewer',required=True);review.add_argument('--decision',choices=['PASS','FAIL'],required=True);review.add_argument('--note',action='append',required=True);review.add_argument('--limitation',action='append',default=[])
    args = parser.parse_args(argv)
    try:
        if args.command=='studio':
            try:
                from vehiclerecon_studio.launcher import launch
            except ImportError:
                print('Studio is optional. Install: python -m pip install -e . -e studio/backend');return 1
            try:launch(roots=args.root,port=args.port,host=args.host,browser=not args.no_browser)
            except (ImportError,ValueError,OSError) as exc:print(str(exc));return 1
            return 0
        if args.command=='init':
            if args.schema_version == 2:
                from .authoring.versions import create_draft
                print(json.dumps(create_draft(args.project,profile=args.profile),indent=2));return 0
            from .core.initialize import initialize
            print(json.dumps(initialize(args.project,args.profile),indent=2));return 0
        if args.command=='migrate':
            from .authoring.versions import preview_migration, execute_migration
            plan=preview_migration(args.project,target=args.to)
            result=plan if args.dry_run else execute_migration(args.project,target=args.to,expected_revision=args.expected_revision or plan['source_revision'])
            print(json.dumps({k:v for k,v in result.items() if k!='documents'},indent=2));return 0
        if args.command=='authoring-status':
            from .authoring.versions import inspect_version
            info=inspect_version(args.project)
            if not info['supported']:
                print(json.dumps(info,indent=2));return 1
            from .authoring.readiness import readiness
            print(json.dumps(readiness(args.project),indent=2));return 0
        project = Project(args.project)
        if args.command=='run':
            from .core.pipeline import Pipeline
            return Pipeline(project,blender=args.blender,use_cache=not args.no_cache).run(until=args.until)
        if args.command=='review':
            from .validation.report import record_review
            print(json.dumps(record_review(project,reviewer=args.reviewer,decision=args.decision,notes=args.note,limitations=args.limitation),indent=2));return 0
        print(json.dumps({'project_id': project.data['project_id'], 'profile': project.data['vehicle_profile'],
                          'root': str(project.root), 'status': 'PASS'}, indent=2))
        return 0
    except ReconError as exc:
        print(f'FAIL: {exc}')
        return 1
