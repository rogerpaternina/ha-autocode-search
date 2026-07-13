"""Persistence layer for Autocode Search."""

from .storage_backend import STORAGE_KEY, StorageBackend
from .success_repository import STORAGE_VERSION, SuccessRepository

__all__ = [
    "STORAGE_KEY",
    "STORAGE_VERSION",
    "StorageBackend",
    "SuccessRepository",
]
