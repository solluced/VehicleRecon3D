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
    else:
        raise ReconError(f'Unsupported Blender stage: {stage}')

if __name__ == '__main__':
    main()
