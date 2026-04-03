import secrets
import uuid

from auth.client import AuthClient
from auth.schemas import UserDetail
from auth.service import UserService
from auth.utils import decode_jwt_token, generate_jwt_token
from exceptions import AuthError, NotFoundError, UnauthorizedError


class AuthHandler:
    def __init__(
        self,
        auth_client: AuthClient,
        user_service: UserService,
    ) -> None:
        self.auth_client = auth_client
        self.user_service = user_service

    def initiate(self) -> tuple[str, str]:
        """Generate a state token and return (state, auth_url)."""
        state = secrets.token_urlsafe(32)
        auth_url = self.auth_client.get_auth_url(state)
        return state, auth_url

    def callback(self, code: str, state: str, stored_state: str | None) -> str:
        """Verify state, exchange code, upsert user. Returns JWT token string."""
        if not stored_state or not secrets.compare_digest(stored_state, state):
            raise AuthError("State token mismatch — possible CSRF attempt")

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

        return generate_jwt_token(user.user_id)

    def me(self, token: str | None) -> UserDetail:
        """Return the current user's profile."""
        if not token:
            raise UnauthorizedError("No JWT cookie present")

        payload = decode_jwt_token(token)
        user_id = uuid.UUID(payload["user_id"])

        user = self.user_service.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        return UserDetail(
            user_id=user.user_id,
            name=user.name,
            profile_url=user.profile_url,
        )
