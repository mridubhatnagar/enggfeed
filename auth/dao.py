import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from auth.models import AllowedUser, User
from exceptions import DatabaseError


class IUserDAO(ABC):
    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID): ...

    @abstractmethod
    def get_by_google_auth_id(self, google_auth_id: str): ...

    @abstractmethod
    def create(self, google_auth_id: str, name: str, email: str, profile_url: str): ...


class UserDAO(IUserDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        try:
            return self.db.query(User).filter(User.user_id == user_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch user by id: {exc}") from exc

    def get_by_google_auth_id(self, google_auth_id: str) -> User | None:
        try:
            return self.db.query(User).filter(User.google_auth_id == google_auth_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch user by google_auth_id: {exc}") from exc

    def create(self, google_auth_id: str, name: str, email: str, profile_url: str) -> User:
        try:
            user = User(
                google_auth_id=google_auth_id,
                name=name,
                email=email,
                profile_url=profile_url,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create user: {exc}") from exc


class IAllowedUserDAO(ABC):
    @abstractmethod
    def get_by_email(self, email: str): ...


class AllowedUserDAO(IAllowedUserDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> AllowedUser | None:
        try:
            return self.db.query(AllowedUser).filter(AllowedUser.email == email).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch allowed user by email: {exc}") from exc
