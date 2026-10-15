"""Explicit production failures (never disabled by python -O)."""

class ReconError(Exception):
    """Invalid input or an executed operation failed."""

class SchemaError(ReconError):
    pass

class ReferenceError(ReconError):
    pass

class GateError(ReconError):
    pass

class BlockedError(ReconError):
    """Missing input, capability, dependency or explicit review."""

class BlenderError(ReconError):
    pass
