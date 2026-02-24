from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PaginatedMeta(BaseModel):
    page: int
    per_page: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PaginatedMeta


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
