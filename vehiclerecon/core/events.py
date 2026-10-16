"""Optional transport-independent observers; observer errors cannot fail a commit."""
import copy


class Events:
    def __init__(self, observers=()):
        self.observers = tuple(observers);self.sequence = 0;self.errors = []

    def emit(self, kind, **data):
        self.sequence += 1
        event = {'kind':kind,'sequence':self.sequence,**data}
        for observer in self.observers:
            try:observer(copy.deepcopy(event))
            except Exception as exc:self.errors.append({'kind':kind,'error':str(exc)})
        return event
