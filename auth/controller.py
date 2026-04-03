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

_STATE_COOKIE = "oauth_state"
_JWT_COOKIE = "access_token"


def get_auth_handler(db: Session = Depends(get_db)) -> AuthHandler:
    user_dao = UserDAO(db)
    user_service = UserService(user_dao)
    auth_client = AuthClient()
    return AuthHandler(
        auth_client=auth_client,
        user_service=user_service,
    )


@router.get("/auth/initiate")
def initiate(
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Set oauth_state httpOnly cookie and return the Google OAuth consent screen URL.
    The frontend is responsible for redirecting to the returned URL."""
    try:
        state, auth_url = handler.initiate()
        response.set_cookie(key=_STATE_COOKIE, value=state, httponly=True, samesite="lax", secure=False)
        return APIResponse(success=True, data={"auth_url": auth_url}, error=None)
    except DatabaseError:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message="Database error"),
        )


@router.get("/auth/callback")
def callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Handle Google OAuth callback, issue JWT cookie."""
    stored_state = request.cookies.get(_STATE_COOKIE)
    try:
        jwt_token = handler.callback(code, state, stored_state)
        response.delete_cookie(_STATE_COOKIE)
        redirect = RedirectResponse(url="/")
        redirect.set_cookie(key=_JWT_COOKIE, value=jwt_token, httponly=True, samesite="lax", secure=False)
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
def me(
    request: Request,
    handler: AuthHandler = Depends(get_auth_handler),
):
    """Return current user profile. Requires JWT cookie."""
    token = request.cookies.get(_JWT_COOKIE)
    try:
        user_detail = handler.me(token)
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
def logout(response: Response):
    """Clear JWT cookie."""
    response.delete_cookie(_JWT_COOKIE)
    return APIResponse(success=True, data={"message": "Logged out"}, error=None)
