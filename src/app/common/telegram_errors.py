"""Helpers for expected Telegram API errors during group lifecycle operations."""

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


def is_group_inaccessible_error(error: Exception) -> bool:
    """True when the bot can no longer access the group (left, kicked, or deleted)."""
    if isinstance(error, TelegramForbiddenError):
        return True
    if isinstance(error, TelegramBadRequest):
        msg = str(error).lower()
        return "chat not found" in msg or "group chat was deleted" in msg
    return False
