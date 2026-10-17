"""Trusted provider registration. No dynamic imports supplied by a project/API."""
from abc import ABC,abstractmethod
import importlib.util
import importlib.metadata

class ProviderUnavailable(ValueError):pass

class CVProvider(ABC):
    id='';capabilities=()
    @abstractmethod
    def metadata(self):raise NotImplementedError
    @abstractmethod
    def run(self,capability,image,parameters,context):raise NotImplementedError

class ProviderRegistry:
    def __init__(self,providers=()):
        self._providers={}
        for p in providers:self.register(p)
    def register(self,provider):
        if not isinstance(provider,CVProvider) or not provider.id or provider.id in self._providers:
            raise ValueError('A provider needs a unique trusted identity')
        self._providers[provider.id]=provider
    def providers(self):return [p.metadata() for p in self._providers.values()]
    def get(self,ident,capability=None):
        p=self._providers.get(ident)
        if p is None or not p.metadata()['available']:raise ProviderUnavailable('Provider unavailable: '+ident)
        if capability is not None and capability not in p.capabilities:raise ProviderUnavailable('Provider capability unavailable')
        return p
    def run(self,ident,capability,image,parameters,context):
        return self.get(ident,capability).run(capability,image,parameters,context)

class OpenCVProvider(CVProvider):
    id='opencv';capabilities=('detect_edges','trace_contour','smart_edge','segment_object','detect_wheels')
    def metadata(self):
        try:version=importlib.metadata.version('opencv-python-headless')
        except importlib.metadata.PackageNotFoundError:version='not installed'
        return {'provider_id':self.id,'name':'OpenCV local baseline','provider_version':version,
                'capabilities':list(self.capabilities),'available':importlib.util.find_spec('cv2') is not None,
                'runtime_requirements':['Optional Studio cv extra','CPU; no model or GPU'],
                'classification':'local','deterministic':True,'semantic_understanding':False}
    def run(self,capability,image,parameters,context):
        from .opencv import run
        return run(capability,image,parameters,context)
