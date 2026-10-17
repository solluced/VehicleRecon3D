"""Bounded, epoch-aware SSE replay. Canonical revision remains the resync source."""
from collections import deque
import threading
import uuid


class EventBus:
    def __init__(self, limit=512):
        self.epoch=uuid.uuid4().hex;self.sequence=0;self.records=deque(maxlen=limit);self.lock=threading.RLock()

    def emit(self, kind, **data):
        with self.lock:
            self.sequence+=1
            record={'id':f'{self.epoch}:{self.sequence}','kind':kind,**data}
            self.records.append(record);return record

    def replay(self, cursor):
        with self.lock:
            ids=[e['id'] for e in self.records]
            if not cursor or cursor not in ids:
                return [{'id':f'{self.epoch}:{self.sequence}','kind':'resync','reason':'New epoch or expired event cursor; reload canonical snapshots'}]
            return list(self.records)[ids.index(cursor)+1:]
