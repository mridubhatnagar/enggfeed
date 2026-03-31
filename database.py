import pickle
from collections.abc import Generator
from functools import wraps

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, make_transient, sessionmaker

from config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_DEFAULT_TIMEOUT = settings.REFRESH_INTERVAL_DAYS * 86400


class Cache:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=False)

    def get(self, key: str):
        data = self._client.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    def _set(self, key: str, value, timeout: int) -> None:
        self._client.setex(key, timeout, pickle.dumps(value))

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def set_str(self, key: str, value: str, timeout: int) -> None:
        self._client.setex(key, timeout, value)

    def get_str(self, key: str) -> str | None:
        data = self._client.get(key)
        return data.decode() if data else None

    @staticmethod
    def make_key(prefix: str, *args) -> str:
        return f"{prefix}:{':'.join(str(a) for a in args)}"

    def cached(self, timeout: int = _DEFAULT_TIMEOUT, key_prefix: str | None = None, unless=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                use_cache = kwargs.pop("use_cache", True)
                force_update = kwargs.pop("force_update", False)

                prefix = key_prefix or func.__qualname__
                key = Cache.make_key(prefix, *args[1:])

                if use_cache and not force_update:
                    cached_val = self.get(key)
                    if cached_val is not None:
                        return cached_val

                result = func(*args, **kwargs)

                should_skip = unless(result) if unless else False
                if use_cache and result is not None and not should_skip:
                    dao_self = args[0]
                    dao_self.db.expunge(result)
                    make_transient(result)
                    self._set(key, result, timeout)

                return result

            return wrapper

        return decorator

    def set(self, key_prefix: str, timeout: int = _DEFAULT_TIMEOUT, key_args: tuple = (0,)):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if result is not None:
                    key_values = tuple(args[i + 1] for i in key_args)
                    key = Cache.make_key(key_prefix, *key_values)
                    dao_self = args[0]
                    dao_self.db.expunge(result)
                    make_transient(result)
                    self._set(key, result, timeout)
                return result

            return wrapper

        return decorator


cache = Cache(settings.REDIS_URL)
