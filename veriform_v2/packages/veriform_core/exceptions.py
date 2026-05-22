class VeriFormRuntimeError(Exception):
    """Base exception for VeriForm runtime."""
    pass

class SyncTimeoutError(VeriFormRuntimeError):
    """Raised when DOM or Network fails to stabilize within budget."""
    pass

class ConvergenceFailedError(VeriFormRuntimeError):
    """Raised when baseline discovery exceeds max attempts."""
    pass

class AntiAutomationBlockError(VeriFormRuntimeError):
    """Raised when WAF or Captcha is detected."""
    pass
