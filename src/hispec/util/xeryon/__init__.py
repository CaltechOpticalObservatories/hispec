"""
Exposes the main public interface for the Xeryon motion control library.

Includes:
- XeryonController: High-level interface for Xeryon motion controllers.
- Stage: Represents a single controllable motion stage.
"""
from .xeryon_controller import XeryonController
from .stage import Stage

__all__ = ["XeryonController", "Stage"]
