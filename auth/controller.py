from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth.client import AuthClient
from auth.dao import UserDAO
from auth.handler import AuthHandler
from auth.schemas import UserDetail
from auth.service import UserService
from database import get_db
from exceptions import (
    AuthError,
    DatabaseError,
    NotFoundError,
    UnauthorizedError,
)
from schemas import APIResponse, ErrorDetail

router = APIRouter(tags=["auth"])


def get_auth_handler(db: Session = Depends(get_db)) -> AuthHandler:
    user_dao = UserDAO(db)
    user_service = UserService(user_dao)
    auth_client = AuthClient()
    return AuthHandler(
        auth_client=auth_client,
        user_service=user_service,
    )


@router.get("/auth/initiate")
async def initiate(
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Set oauth_state httpOnly cookie and return the Google OAuth consent screen URL.
    The frontend is responsible for redirecting to the returned URL."""
    try:
        url = handler.initiate(response)
        return APIResponse(success=True, data={"auth_url": url}, error=None)
    except DatabaseError:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message="Database error"),
        )


@router.get("/auth/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Handle Google OAuth callback, issue JWT cookie."""
    try:
        redirect = RedirectResponse(url="/")
        handler.callback(code, state, request, redirect)
        return redirect
    except AuthError:
        return RedirectResponse(url="/?error=auth_failed")
    except DatabaseError:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message="Database error"),
        )


@router.get("/auth/me", response_model=APIResponse[UserDetail])
async def me(
    request: Request,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Return current user profile. Requires JWT cookie."""
    try:
        user_detail = handler.me(request)
        return APIResponse(success=True, data=user_detail, error=None)
    except UnauthorizedError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=401, message=str(exc)),
        )
    except NotFoundError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=404, message=str(exc)),
        )
    except DatabaseError:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message="Database error"),
        )


@router.post("/auth/logout")
async def logout(
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Clear JWT cookie."""
    handler.logout(response)
    return APIResponse(success=True, data={"message": "Logged out"}, error=None)
