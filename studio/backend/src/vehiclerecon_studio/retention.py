"""Small byte/count-bounded transport replay cache, separate from core undo."""
from collections import OrderedDict
import json


class Responses:
    def __init__(self,*,limit=128,byte_limit=8*1024*1024):
        self.limit=limit;self.byte_limit=byte_limit;self.items=OrderedDict();self.retained_bytes=0

    def get(self,key):
        entry=self.items.get(key)
        if entry is None:return None
        self.items.move_to_end(key);return entry[0]

    def __setitem__(self,key,value):
        size=len(json.dumps(value,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode())
        if key in self.items:self.retained_bytes-=self.items.pop(key)[1]
        if size>self.byte_limit:return
        self.items[key]=(value,size);self.retained_bytes+=size
        while len(self.items)>self.limit or self.retained_bytes>self.byte_limit:
            _,(_,removed)=self.items.popitem(last=False);self.retained_bytes-=removed

    def __len__(self):return len(self.items)

    def __iter__(self):return iter(self.items)

    def pop(self,key):
        value,size=self.items.pop(key);self.retained_bytes-=size;return value
