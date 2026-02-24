from fastapi import APIRouter

from app.auth.dependencies import require_role
from app.models.orm.user import User

router = APIRouter()


@router.get("")
async def list_audit_logs(current_user: User = require_role("OPS", "ADM")):
    """List audit logs - TODO"""
    return {"success": True, "data": []}
