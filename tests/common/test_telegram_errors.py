from unittest.mock import MagicMock

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.app.common.telegram_errors import is_group_inaccessible_error


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
