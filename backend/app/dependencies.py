"""
Re-export dependencies for app.dependencies compatibility.
"""
from app.core.dependencies import (
    get_current_user,
    get_current_business,
    oauth2_scheme,
    get_db,
)

__all__ = ["get_current_user", "get_current_business", "oauth2_scheme", "get_db"]
