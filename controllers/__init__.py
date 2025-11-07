"""
Controller layer initialization.
Controllers handle HTTP request/response logic and coordinate between routes and services.
"""

from .activity_controller import ActivityController

__all__ = [
    "ActivityController",
]
