"""Single background-worker entry. Host validates schemas before execution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from vehiclerecon.core.project import Project
from vehiclerecon.core.errors import ReconError

def main():
    args = sys.argv[sys.argv.index('--')+1:]
    project = Project(args[0], check=False)
    stage = args[1]
    if stage == 'initialize':
        from vehiclerecon.blender.scene import initialize, save
        initialize(project)
        save(project.path('.cache/initialize.blend'))
    elif stage == 'calibration':
        from vehiclerecon.blender.scene import initialize
        from vehiclerecon.blender.reference import build
        initialize(project)
        build(project)
    elif stage == 'cage':
        from vehiclerecon.blender.cage import build
        build(project)
    elif stage == 'surfaces':
        from vehiclerecon.blender.surfaces import build
        build(project)
    elif stage == 'surface_masks':
        from vehiclerecon.blender.silhouette import validate
        validate(project,'surface')
    elif stage == 'details':
        from vehiclerecon.blender.details import build
        build(project)
    elif stage == 'final_masks':
        from vehiclerecon.blender.silhouette import validate
        validate(project,'final')
    elif stage == 'cleanup':
        from vehiclerecon.blender.audit import cleanup
        cleanup(project)
    elif stage == 'audit':
        from vehiclerecon.blender.audit import audit
        audit(project)
    elif stage == 'presentation':
        from vehiclerecon.blender.presentation import build
        build(project)
    elif stage == 'export':
        from vehiclerecon.blender.export import export
        export(project)
    elif stage == 'overlay':
        from vehiclerecon.blender.overlay import build
        build(project)
    else:
        raise ReconError(f'Unsupported Blender stage: {stage}')

if __name__ == '__main__':
    main()
