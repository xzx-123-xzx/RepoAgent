"""Shared HTTP client SSL configuration."""

from __future__ import annotations

from typing import Union

from app.config import get_settings
from common.logger import my_logger

logger = my_logger
_ssl_verify: Union[bool, str] | None = None


def get_ssl_verify() -> Union[bool, str]:
    """Return httpx `verify` value: certifi CA bundle, True, or False."""
    global _ssl_verify
    if _ssl_verify is not None:
        return _ssl_verify

    settings = get_settings()
    if not settings.HTTP_SSL_VERIFY:
        logger.warning("HTTP_SSL_VERIFY=false，已关闭 SSL 证书校验（仅建议开发环境使用）")
        _ssl_verify = False
        return _ssl_verify

    try:
        import certifi

        _ssl_verify = certifi.where()
    except ImportError:
        _ssl_verify = True

    return _ssl_verify
