import uuid

from auth.dao import IUserDAO


class UserService:
    def __init__(self, dao: IUserDAO) -> None:
        self.dao = dao

    def get_user_by_id(self, user_id: uuid.UUID):
        return self.dao.get_by_id(user_id)

    def get_user_by_auth_id(self, google_auth_id: str):
        return self.dao.get_by_google_auth_id(google_auth_id)

    def create_user(self, google_auth_id: str, name: str, email: str, profile_url: str):
        return self.dao.create(google_auth_id, name, email, profile_url)

