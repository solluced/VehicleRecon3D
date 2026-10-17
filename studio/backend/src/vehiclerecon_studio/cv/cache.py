"""Byte/count bounded disposable CV values. No project-owned executable data."""
from collections import OrderedDict
import copy,json,threading

def size(value):
    if hasattr(value,'nbytes'):return value.nbytes
    if isinstance(value,bytes):return len(value)
    if isinstance(value,dict):return sum(len(str(k))+size(v) for k,v in value.items())
    if isinstance(value,(list,tuple)):return sum(size(v) for v in value)
    return len(json.dumps(value,allow_nan=False).encode())

class ByteCache:
    def __init__(self,limit=64*1024*1024,count=64):
        self.limit=limit;self.count=count;self.items=OrderedDict();self.bytes=0;self.lock=threading.RLock()
    def get(self,key):
        with self.lock:
            found=self.items.get(key)
            if found is None:return None
            self.items.move_to_end(key);return found[0]
    def put(self,key,value):
        n=size(value)
        with self.lock:
            self.drop(key)
            if n>self.limit:return
            self.items[key]=(value,n);self.bytes+=n
            while len(self.items)>self.count or self.bytes>self.limit:self.drop(next(iter(self.items)))
    def drop(self,key):
        with self.lock:
            found=self.items.pop(key,None)
            if found:self.bytes-=found[1]
    def clear(self):
        with self.lock:self.items.clear();self.bytes=0
