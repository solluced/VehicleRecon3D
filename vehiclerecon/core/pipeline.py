"""Stage result vocabulary; orchestration is introduced in phase 08."""
from dataclasses import dataclass, field
from enum import Enum

class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    BLOCKED = "BLOCKED"

@dataclass
class StageResult:
    stage: str
    status: Status
    message: str = ""
    outputs: list = field(default_factory=list)

    @property
    def exit_code(self):
        return 0 if self.status in (Status.PASS, Status.SKIP) else 1
