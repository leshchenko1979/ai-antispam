import json
from unittest.mock import MagicMock

import pytest
from aiogram.exceptions import TelegramNetworkError

from src.app.main import WEBHOOK_TIMEOUT, handle_unhandled_exception


@pytest.mark.asyncio
async def test_handle_unhandled_exception_returns_503_for_transient():
    span = MagicMock()
    err = TelegramNetworkError(method=MagicMock(), message="network down")
    response = await handle_unhandled_exception(span, err, {"update_id": 1}, elapsed=1.0)
    assert response.status == 503
    body = json.loads(response.text)
    assert body.get("retry") is True
    assert span.tags == ["webhook_retryable_error"]


@pytest.mark.asyncio
async def test_handle_unhandled_exception_acks_unknown():
    span = MagicMock()
    response = await handle_unhandled_exception(
        span, RuntimeError("bug"), {"update_id": 1}, elapsed=1.0
    )
    assert response.status == 200
    assert span.tags == ["unhandled_exception"]


@pytest.mark.asyncio
async def test_handle_unhandled_exception_no_retry_when_no_time_left():
    span = MagicMock()
    err = TelegramNetworkError(method=MagicMock(), message="network")
    elapsed = float(WEBHOOK_TIMEOUT - 1)
    response = await handle_unhandled_exception(span, err, {"update_id": 1}, elapsed=elapsed)
    assert response.status == 200


def test_main_imports():
    pass
