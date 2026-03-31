import urllib.parse

import httpx

from config import settings
from exceptions import AuthError


class AuthClient:
    """Wraps Google OAuth HTTP calls."""

    def get_auth_url(self, state: str) -> str:
        """Build the Google OAuth consent screen URL."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> str:
        """Exchange the authorization code for a raw Google ID token string."""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        try:
            response = httpx.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPStatusError as exc:
            raise AuthError(f"Google token exchange failed (HTTP {exc.response.status_code})") from exc
        except Exception as exc:
            raise AuthError(f"Failed to exchange code with Google: {exc}") from exc

        id_token_str = token_data.get("id_token")
        if not id_token_str:
            raise AuthError("Google token response did not include id_token")
        return id_token_str

    def verify_id_token(self, id_token_str: str) -> dict:
        """Verify the Google ID token via Google's tokeninfo endpoint and return claims.

        Raises AuthError if verification fails or email is not verified.
        Uses Google's tokeninfo endpoint — no google-auth library needed.
        """
        try:
            response = httpx.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token_str},
                timeout=10,
            )
            response.raise_for_status()
            claims = response.json()
        except httpx.HTTPStatusError as exc:
            raise AuthError(f"ID token verification failed (HTTP {exc.response.status_code})") from exc
        except Exception as exc:
            raise AuthError(f"ID token verification failed: {exc}") from exc

        # Verify audience matches our client_id
        aud = claims.get("aud", "")
        if aud != settings.GOOGLE_CLIENT_ID:
            raise AuthError("ID token audience does not match client_id")

        if not claims.get("email_verified") in (True, "true"):
            raise AuthError("Google account email is not verified")

        return claims
