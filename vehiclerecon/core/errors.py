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

class ConflictError(ReconError):
    """An expected revision, stable binding or external file identity changed."""

class LockError(ConflictError):
    """Another thread/process owns the project mutation lock."""
