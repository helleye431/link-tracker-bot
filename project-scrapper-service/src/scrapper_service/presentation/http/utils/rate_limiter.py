from typing import Literal
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter_period = Literal[
    "second",
    "minute",
    "hour",
    "day",
    "month",
    "year",
]


def rate_limiter(request_limit: int, request_limit_period: limiter_period):
    limit = f"{request_limit}/{request_limit_period}"
    return Limiter(key_func=get_remote_address, application_limits=[limit])
