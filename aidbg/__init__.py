"""
aidbg - AI Black Box Debugger
Collect evidence -> reconstruct execution -> identify probable root cause -> explain it clearly -> suggest a safe fix.
"""

__version__ = "0.1.0"

from aidbg.agent.collector import init, capture_exception, observe
from aidbg.agent.context import set_tag, add_breadcrumb

__all__ = ["init", "capture_exception", "observe", "set_tag", "add_breadcrumb"]
