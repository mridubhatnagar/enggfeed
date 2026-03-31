from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: int
    message: str


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None
