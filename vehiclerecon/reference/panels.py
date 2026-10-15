"""Input panel selection and decoded-format identities without Blender."""
import struct
from ..core.errors import ReferenceError
from ..core.manifest import digest_file

def png_size(path):
    # Historic callers use this name; detect bytes, never trust file suffixes.
    raw = path.read_bytes()
    if raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR':
        return list(struct.unpack('>II',raw[16:24]))
    if raw[:2] == b'\xff\xd8':
        cursor = 2
        while cursor+4 <= len(raw):
            if raw[cursor] != 255:
                raise ReferenceError(f'Invalid JPEG marker: {path}')
            while raw[cursor] == 255:
                cursor += 1
            marker = raw[cursor]
            cursor += 1
            length = struct.unpack_from('>H',raw,cursor)[0]
            if marker in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                height,width = struct.unpack_from('>HH',raw,cursor+3)
                return [width,height]
            if length < 2:
                break
            cursor += length
    raise ReferenceError(f'Unsupported/corrupt image (PNG/JPEG required): {path}')

def select_panel(project, view, config):
    path = project.path(project.data['references'].get(view,project.data['references']['multiview']), exists=True)
    separate = view in project.data['references']
    crop = config['crop']
    expected = [crop[2]-crop[0],crop[3]-crop[1]] if separate else None
    if expected and png_size(path) != expected:
        raise ReferenceError(f'{view}: separate image size must match its calibrated panel framing {expected}; update calibration')
    return path, separate

def inventory(project):
    return {name:{'path':path,'size':png_size(project.path(path,exists=True)),
                  'sha256':digest_file(project.path(path,exists=True))}
            for name,path in project.data['references'].items()}
