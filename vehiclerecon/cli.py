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
    init=commands.add_parser('init');init.add_argument('project');init.add_argument('--profile',default='sedan')
    run=commands.add_parser('run');run.add_argument('project');run.add_argument('--blender');run.add_argument('--no-cache',action='store_true');run.add_argument('--until',choices=['preflight','references','calibration','overlay','cage','surfaces','silhouette','details','geometry','presentation','export','glb_verify','viewer','delivery'])
    review=commands.add_parser('review');review.add_argument('project');review.add_argument('--reviewer',required=True);review.add_argument('--decision',choices=['PASS','FAIL'],required=True);review.add_argument('--note',action='append',required=True);review.add_argument('--limitation',action='append',default=[])
    args = parser.parse_args(argv)
    try:
        if args.command=='init':
            from .core.initialize import initialize
            print(json.dumps(initialize(args.project,args.profile),indent=2));return 0
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
