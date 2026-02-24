"""Global dependency injection utilities."""
from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_role

__all__ = ["get_db", "get_current_user", "require_role"]
