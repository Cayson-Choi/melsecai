"""Custom exception hierarchy for MELSEC Ladder Generator."""


class MelsecError(Exception):
    """Base exception for all MELSEC ladder generator errors."""


class DeviceError(MelsecError):
    """Device allocation or addressing errors."""


class DeviceConflictError(DeviceError):
    """Raised when a device address is already allocated."""


class DeviceRangeError(DeviceError):
    """Raised when a device address exceeds valid range."""


class CompilerError(MelsecError):
    """Ladder-to-IL compilation errors."""


class StackImbalanceError(CompilerError):
    """Raised when MPS/MRD/MPP stack is unbalanced."""


class ValidationError(MelsecError):
    """IL instruction validation errors."""


class PatternError(MelsecError):
    """Pattern matching or generation errors."""


class PatternNotFoundError(PatternError):
    """Raised when no matching pattern is found."""


class ExportError(MelsecError):
    """GX Works2 export errors."""


class TimingAnalysisError(MelsecError):
    """Timing diagram analysis errors."""
