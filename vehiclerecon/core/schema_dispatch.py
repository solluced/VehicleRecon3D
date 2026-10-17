"""Equivalent oneOf dispatch for uniquely required string discriminators."""
from functools import lru_cache
from collections import OrderedDict
from contextvars import ContextVar
from contextlib import contextmanager
import hashlib
import json
import threading

_namespace=ContextVar('schema_validation_namespace',default=None)
_guard=threading.RLock()
_choices=OrderedDict()
_valid=OrderedDict()
_bytes=0


@contextmanager
def validation_namespace(schemas,identity=None):
    """Bind structural memoization to every exact schema, including $refs."""
    identity=identity or hashlib.sha256(json.dumps(schemas,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    marker=_namespace.set(identity)
    try:yield
    finally:_namespace.reset(marker)


def cache_key(choices,instance):
    namespace=_namespace.get()
    if namespace is None:return None
    from .project import _json_types
    if not _json_types(instance):return None
    try:raw=json.dumps(instance,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (TypeError,ValueError):return None
    if len(raw)>65536:return None
    with _guard:
        identity=id(choices);entry=_choices.get(identity)
        if entry is None or entry[0] is not choices:
            signature=hashlib.sha256(json.dumps(choices,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            _choices[identity]=(choices,signature)
            if len(_choices)>32:_choices.popitem(last=False)
        else:signature=entry[1]
    return namespace,signature,raw


def remember(key):
    global _bytes
    with _guard:
        if key not in _valid:_valid[key]=True;_bytes+=len(key[2])
        _valid.move_to_end(key)
        while len(_valid)>8192 or _bytes>8*1024*1024:
            old,_=_valid.popitem(last=False);_bytes-=len(old[2])


@lru_cache(maxsize=1)
def authoring_validator():
    from jsonschema import Draft202012Validator, validators
    original=Draft202012Validator.VALIDATORS['oneOf']

    def one_of(validator, choices, instance, schema):
        if isinstance(instance,dict):
            for name in ('kind','type'):
                if not isinstance(instance.get(name),str):continue
                tags=[c.get('properties',{}).get(name,{}).get('const') if isinstance(c,dict) and name in c.get('required',[]) else None for c in choices]
                if tags and all(isinstance(t,str) for t in tags) and len(set(tags))==len(tags) and instance[name] in tags:
                    # Every other branch must fail its required const. Validate
                    # every constraint in the selected branch; never skip it.
                    index=tags.index(instance[name])
                    key=cache_key(choices,instance) if name=='kind' else None
                    if key is not None:
                        with _guard:
                            if key in _valid:_valid.move_to_end(key);return
                    errors=list(validator.descend(instance,choices[index],schema_path=index))
                    if not errors and key is not None:remember(key)
                    yield from errors
                    return
        yield from original(validator,choices,instance,schema)

    return validators.extend(Draft202012Validator,{'oneOf':one_of})
