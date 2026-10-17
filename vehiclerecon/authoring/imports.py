"""Generic immutable reference registration; decoders enforce their own budgets."""
import hashlib
import os
from ..core.errors import ConflictError, ReferenceError
from ..core.locking import ProjectLock
from ..core.revisions import revision
from ..reference.panels import png_size


def import_reference(session, raw, *, reference_id='multiview', expected_revision):
    """Preserve exact bytes; failed registration may leave an unreferenced source."""
    with ProjectLock(session.root,'reference-import',expected_revision):
        if revision(session.root)!=expected_revision:raise ConflictError('CONFLICT: source import revision changed')
        sha=hashlib.sha256(raw).hexdigest()
        extension='png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if raw.startswith(b'\xff\xd8') else None
        if extension is None:raise ReferenceError('PNG/JPEG image required')
        from .workspace import Workspace
        w=Workspace(session.root);relative='input/'+sha+'.'+extension
        path=w.project.path(relative);path.parent.mkdir(exist_ok=True)
        path=w.project.path(relative)
        try:
            with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        except FileExistsError:
            if path.read_bytes()!=raw:raise ConflictError('Immutable source identity collision')
        size=png_size(path)
        result=session.apply([{'type':'RegisterReference','reference_id':reference_id,'path':relative,
                               'sha256':sha,'size':size}],expected_revision=expected_revision)
        return {**result,'reference_id':reference_id,'sha256':sha,'size':size}

def replace_source_view(session,raw,*,view,expected_revision):
    """Retain original sources and observations; new framing is explicitly stale."""
    if view not in ('front','side','rear','top'):raise ReferenceError('Unknown replacement source view')
    with ProjectLock(session.root,'source-replacement',expected_revision):
        if revision(session.root)!=expected_revision:raise ConflictError('Replacement source revision changed')
        from .workspace import Workspace
        w=Workspace(session.root);sha=hashlib.sha256(raw).hexdigest()
        extension='png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if raw.startswith(b'\xff\xd8') else None
        if extension is None:raise ReferenceError('PNG/JPEG image required')
        relative='input/'+sha+'.'+extension;path=w.project.path(relative);path.parent.mkdir(exist_ok=True)
        path=w.project.path(relative)
        try:
            with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        except FileExistsError:
            if path.read_bytes()!=raw:raise ConflictError('Immutable source identity collision')
        size=png_size(path)
        result=session.apply([{'type':'ReplaceSourceView','view':view,'path':relative,'sha256':sha,'size':size,'confirm_replacement':True}],expected_revision=expected_revision)
        return {**result,'reference_id':'source_'+sha,'sha256':sha,'size':size}
