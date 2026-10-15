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
    args = parser.parse_args(argv)
    try:
        project = Project(args.project)
        print(json.dumps({'project_id': project.data['project_id'], 'profile': project.data['vehicle_profile'],
                          'root': str(project.root), 'status': 'PASS'}, indent=2))
        return 0
    except ReconError as exc:
        print(f'FAIL: {exc}')
        return 1
