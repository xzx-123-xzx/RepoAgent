"""Application settings wrapping common Config."""

from functools import lru_cache

from common.config import Config


@lru_cache
def get_settings() -> Config:
    return Config()
