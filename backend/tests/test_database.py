import asyncio
from unittest.mock import patch

import pytest

from app import database


@pytest.fixture(autouse=True)
def reset_worker_loop() -> None:
    database._worker_event_loop = None
    yield
    if (
        database._worker_event_loop is not None
        and not database._worker_event_loop.is_closed()
    ):
        database._worker_event_loop.close()
    database._worker_event_loop = None


def test_run_db_reuses_event_loop_across_calls() -> None:
    async def first() -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    async def second() -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    loop_one = database.run_db(first())
    loop_two = database.run_db(second())

    assert loop_one is loop_two
    assert loop_one is database._get_worker_event_loop()
    assert not loop_one.is_closed()


def test_run_db_fn_delegates_to_run_db() -> None:
    async def sample(conn: object) -> str:
        return "ok"

    with patch.object(database, "run_db", return_value="ok") as mock_run_db:
        result = database.run_db_fn(sample)

    assert result == "ok"
    mock_run_db.assert_called_once()
