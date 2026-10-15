"""Deterministic render containers without touching image pixels/color profiles."""
import struct
from ..core.errors import GateError

def stable_png(raw):
    if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise GateError('Expected PNG render')
    parts=[raw[:8]];cursor=8
    while cursor<len(raw):
        if cursor+12>len(raw):raise GateError('Truncated PNG chunk')
        length=struct.unpack_from('>I',raw,cursor)[0];end=cursor+length+12
        if end>len(raw):raise GateError('Truncated PNG data')
        tag=raw[cursor+4:cursor+8]
        # Blender writes Date, RenderTime and Cycles timing statistics here.
        # Keep IDAT, ICC/gamma/chromaticity and all non-text chunks byte-for-byte.
        if tag not in (b'tEXt',b'iTXt',b'zTXt'):parts.append(raw[cursor:end])
        cursor=end
    return b''.join(parts)
