"""Helpers for expected Telegram API errors during group lifecycle operations."""

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

_INACCESSIBLE_MESSAGE_MARKERS = (
    "chat not found",
    "group chat was deleted",
    "bot was kicked",
    "bot is not a member of the group",
    "bot is not a member of the supergroup",
)


def _message_indicates_inaccessible(error: Exception) -> bool:
    msg = str(error).lower()
    return any(marker in msg for marker in _INACCESSIBLE_MESSAGE_MARKERS)


def is_group_inaccessible_error(error: Exception) -> bool:
    """True when the bot can no longer access the group (left, kicked, or deleted)."""
    if isinstance(error, (TelegramForbiddenError, TelegramBadRequest)):
        return _message_indicates_inaccessible(error)
    return False
