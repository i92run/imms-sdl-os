"""Custom exception classes for hardware and workflow errors."""

class HardwareConnectionError(Exception):
    """Raised when a hardware device cannot be reached over the network."""
    pass

class XPRDoorError(Exception):
    """Raised when the draft shield doors fail to open or close properly."""
    pass