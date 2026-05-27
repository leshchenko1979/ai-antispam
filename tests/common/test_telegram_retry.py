from unittest.mock import MagicMock

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from src.app.common.utils import retry_on_network_error


@pytest.mark.asyncio
async def test_retry_on_network_error_retries_telegram_network():
    calls = 0

    @retry_on_network_error
    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise TelegramNetworkError(method=MagicMock(), message="network")
        return "ok"

    assert await flaky() == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_retry_on_network_error_does_not_retry_bad_request():
    calls = 0

    @retry_on_network_error
    async def bad():
        nonlocal calls
        calls += 1
        raise TelegramBadRequest(method=MagicMock(), message="Bad Request")

    with pytest.raises(TelegramBadRequest):
        await bad()
    assert calls == 1


@pytest.mark.asyncio
async def test_retry_on_network_error_honors_retry_after(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("src.app.common.utils.asyncio.sleep", fake_sleep)

    calls = 0

    @retry_on_network_error
    async def flood():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise TelegramRetryAfter(
                method=MagicMock(), message="Too Many Requests", retry_after=2
            )
        return "ok"

    assert await flood() == "ok"
    assert calls == 2
    assert sleeps == [2]
