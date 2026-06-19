from __future__ import annotations


class TypeConfirmationRequired(Exception):
    """Raised when post_type confidence is below threshold and user must confirm."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
