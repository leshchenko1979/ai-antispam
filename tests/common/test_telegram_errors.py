from unittest.mock import MagicMock

import asyncpg
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramServerError,
)

from src.app.common.telegram_errors import (
    is_bot_to_bot_disabled_error,
    is_group_inaccessible_error,
    is_message_not_found_error,
    is_permission_error,
    is_webhook_retryable,
)


def test_is_group_inaccessible_error_chat_not_found():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: chat not found"
    )
    assert is_group_inaccessible_error(err) is True


def test_is_group_inaccessible_error_bot_kicked():
    err = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden: bot was kicked from the group chat"
    )
    assert is_group_inaccessible_error(err) is True


def test_is_group_inaccessible_error_unrelated_bad_request():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: can't parse entities"
    )
    assert is_group_inaccessible_error(err) is False


def test_is_group_inaccessible_error_unrelated_forbidden():
    err = TelegramForbiddenError(
        method=MagicMock(),
        message="Forbidden: bot can't initiate conversation with a user",
    )
    assert is_group_inaccessible_error(err) is False


def test_is_group_inaccessible_error_group_chat_deleted():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: group chat was deleted"
    )
    assert is_group_inaccessible_error(err) is True


def test_is_group_inaccessible_error_bot_not_member():
    err = TelegramForbiddenError(
        method=MagicMock(),
        message="Forbidden: bot is not a member of the group chat",
    )
    assert is_group_inaccessible_error(err) is True


def test_is_group_inaccessible_error_non_telegram():
    assert is_group_inaccessible_error(RuntimeError("network")) is False


def test_is_group_inaccessible_error_not_found_with_marker():
    err = TelegramNotFound(method=MagicMock(), message="Not Found: chat not found")
    assert is_group_inaccessible_error(err) is True


def test_is_group_inaccessible_error_not_found_unrelated():
    err = TelegramNotFound(method=MagicMock(), message="Not Found: user not found")
    assert is_group_inaccessible_error(err) is False


def test_is_permission_error_delete_rights():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: not enough rights to delete"
    )
    assert is_permission_error(err) is True


def test_is_permission_error_unrelated_bad_request():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: can't parse entities"
    )
    assert is_permission_error(err) is False


def test_is_permission_error_forbidden_not_checked():
    err = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden: not enough rights"
    )
    assert is_permission_error(err) is False


def test_is_message_not_found_error_delete():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: message to delete not found"
    )
    assert is_message_not_found_error(err) is True


def test_is_message_not_found_error_unrelated():
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: chat not found"
    )
    assert is_message_not_found_error(err) is False


def test_is_webhook_retryable_telegram_network():
    err = TelegramNetworkError(method=MagicMock(), message="Network error")
    assert is_webhook_retryable(err) is True


def test_is_webhook_retryable_telegram_server():
    err = TelegramServerError(method=MagicMock(), message="Server error")
    assert is_webhook_retryable(err) is True


def test_is_webhook_retryable_connection_error():
    assert is_webhook_retryable(ConnectionError("reset")) is True


def test_is_webhook_retryable_postgres_connection():
    assert is_webhook_retryable(asyncpg.PostgresConnectionError("down")) is True


def test_is_webhook_retryable_bad_request():
    err = TelegramBadRequest(method=MagicMock(), message="Bad Request")
    assert is_webhook_retryable(err) is False


def test_is_webhook_retryable_unknown():
    assert is_webhook_retryable(RuntimeError("bug")) is False


def test_is_bot_to_bot_disabled_error():
    """Bots cannot receive DMs from other bots unless user allows it."""
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: USER_BOT_TO_BOT_DISABLED"
    )
    assert is_bot_to_bot_disabled_error(err) is True


def test_is_bot_to_bot_disabled_error_unrelated():
    """Unrelated errors should not be classified as bot-to-bot disabled."""
    err = TelegramBadRequest(
        method=MagicMock(), message="Bad Request: chat not found"
    )
    assert is_bot_to_bot_disabled_error(err) is False


def test_is_bot_to_bot_disabled_error_non_telegram():
    """Non-Telegram errors should not match."""
    assert is_bot_to_bot_disabled_error(RuntimeError("network")) is False
