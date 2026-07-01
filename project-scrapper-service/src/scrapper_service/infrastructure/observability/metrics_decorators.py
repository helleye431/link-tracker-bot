from collections.abc import Awaitable, Callable, Mapping
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar
from scrapper_service.infrastructure.observability.metrics import (
    request_duration_ms_total,
)

from scrapper_service.infrastructure.observability.metrics import links_on_track_total

P = ParamSpec("P")
R = TypeVar("R")


SourceCounts = Mapping[str, int]


def observe_links_on_track(
    tracked_sources: tuple[str, ...] = ("github", "stackoverflow"),
) -> Callable[
    [Callable[P, Awaitable[SourceCounts]]], Callable[P, Awaitable[SourceCounts]]
]:
    def decorator(
        func: Callable[P, Awaitable[SourceCounts]],
    ) -> Callable[P, Awaitable[SourceCounts]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> SourceCounts:
            counts = await func(*args, **kwargs)

            for source in tracked_sources:
                links_on_track_total.labels(tracked_source=source).set(
                    counts.get(source, 0)
                )

            return counts

        return wrapper

    return decorator


def observe_request_duration(scope: str, scope_type: str):
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            started_at = perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                request_duration_ms_total.labels(
                    scope=scope,
                    scope_type=scope_type,
                ).observe((perf_counter() - started_at) * 1000)

        return wrapper

    return decorator
