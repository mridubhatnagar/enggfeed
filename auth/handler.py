import secrets

from fastapi import Request, Response

from auth.client import AuthClient
from auth.schemas import UserDetail
from auth.service import UserService
from auth.utils import decode_jwt_token, generate_jwt_token
from exceptions import AuthError, NotFoundError, UnauthorizedError

_STATE_COOKIE = "oauth_state"
_JWT_COOKIE = "access_token"


class AuthHandler:
    def __init__(
        self,
        auth_client: AuthClient,
        user_service: UserService,
    ) -> None:
        self.auth_client = auth_client
        self.user_service = user_service

    def initiate(self, response: Response) -> str:
        """Generate a state token, store it in an httpOnly cookie, and return the
        Google OAuth consent screen URL."""
        state = secrets.token_urlsafe(32)
        response.set_cookie(
            key=_STATE_COOKIE,
            value=state,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return self.auth_client.get_auth_url(state)

    def callback(self, code: str, state: str, request: Request, response: Response) -> str:
        """Complete the OAuth flow: verify state, exchange code, validate user,
        issue JWT cookie. Returns success message."""
        stored_state = request.cookies.get(_STATE_COOKIE)
        if not stored_state or not secrets.compare_digest(stored_state, state):
            raise AuthError("State token mismatch — possible CSRF attempt")
        response.delete_cookie(_STATE_COOKIE)

        id_token_str = self.auth_client.exchange_code(code)

        claims = self.auth_client.verify_id_token(id_token_str)
        email: str = claims.get("email", "")
        google_auth_id: str = claims.get("sub", "")
        name: str = claims.get("name", "")
        profile_url: str = claims.get("picture", "")

        user = self.user_service.get_user_by_auth_id(google_auth_id)
        if user is None:
            user = self.user_service.create_user(
                google_auth_id=google_auth_id,
                name=name,
                email=email,
                profile_url=profile_url,
            )

        token = generate_jwt_token(user.user_id)
        response.set_cookie(
            key=_JWT_COOKIE,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,  # set True in production behind TLS
        )
        return "Login successful"

    def me(self, request: Request) -> UserDetail:
        """Return the current user's profile from the JWT cookie."""
        token = request.cookies.get(_JWT_COOKIE)
        if not token:
            raise UnauthorizedError("No JWT cookie present")

        payload = decode_jwt_token(token)
        import uuid
        user_id = uuid.UUID(payload["user_id"])

        user = self.user_service.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        return UserDetail(
            user_id=user.user_id,
            name=user.name,
            profile_url=user.profile_url,
        )

    def logout(self, response: Response) -> None:
        """Clear the JWT cookie."""
        response.delete_cookie(_JWT_COOKIE)
