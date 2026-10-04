"""Explicit failure taxonomy for CDSE ingestion (Module 1)."""
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    AUTHENTICATION_FAILED         = "AUTHENTICATION_FAILED"
    INVALID_REQUEST               = "INVALID_REQUEST"
    INVALID_AOI                   = "INVALID_AOI"
    INVALID_DATE_RANGE            = "INVALID_DATE_RANGE"
    INVALID_CLOUD_THRESHOLD       = "INVALID_CLOUD_THRESHOLD"
    NO_PRODUCTS_FOUND             = "NO_PRODUCTS_FOUND"
    NO_PRODUCTS_WITHIN_CLOUD_LIMIT = "NO_PRODUCTS_WITHIN_CLOUD_LIMIT"
    CATALOG_QUERY_FAILED          = "CATALOG_QUERY_FAILED"
    PRODUCT_METADATA_INVALID      = "PRODUCT_METADATA_INVALID"
    DOWNLOAD_FAILED               = "DOWNLOAD_FAILED"
    DOWNLOAD_TIMEOUT              = "DOWNLOAD_TIMEOUT"
    INSUFFICIENT_STORAGE          = "INSUFFICIENT_STORAGE"
    PRODUCT_INTEGRITY_FAILED      = "PRODUCT_INTEGRITY_FAILED"
    CACHE_CORRUPTED               = "CACHE_CORRUPTED"


class IngestionError(RuntimeError):
    """Base error for all ingestion failures.

    Attributes:
        code:    machine-readable ErrorCode.
        message: human-readable message (safe to log; no secrets).
        context: extra structured info (safe to log; NEVER credentials).
    """

    def __init__(self, code: ErrorCode, message: str,
                 context: dict[str, Any] | None = None) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context,
        }


__all__ = ["ErrorCode", "IngestionError"]
