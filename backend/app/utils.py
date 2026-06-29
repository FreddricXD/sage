from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


def run_async(coro: Awaitable[T]) -> T:
    """Run an async coroutine from synchronous code.

    Used by background ingestion tasks (which run in a worker thread without a
    running event loop) to call the async AI providers.
    """
    return asyncio.run(coro)
