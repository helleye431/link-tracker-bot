import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    wait_exponential,
)
from scrapper_service.application.exceptions.resilient_exceptions import (
    RetryableHTTPStatusError,
)
from aiomisc import CircuitBreaker


class ResilientHttpClient:
    def __init__(
        self,
        timeout_seconds: float,
        retry_attempts: int,
        retry_backoff_seconds: float,
        retry_enable_exponential_backoff: bool,
        retryable_status_codes: list[int],
        circuit_error_ratio: float,
        circuit_response_time: float,
        circuit_recovery_time: float,
        circuit_broken_time: float,
    ) -> None:
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))
        self.retry_attempts = retry_attempts
        self.wait_scenario = (
            wait_exponential(retry_backoff_seconds)
            if retry_enable_exponential_backoff
            else wait_fixed(retry_backoff_seconds)
        )
        self.retryable_status_codes = retryable_status_codes
        self.circuit_breaker = CircuitBreaker(
            error_ratio=circuit_error_ratio,
            response_time=circuit_response_time,
            exceptions=[Exception],
            recovery_time=circuit_recovery_time,
            broken_time=circuit_broken_time,
        )

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        @retry(
            stop=stop_after_attempt(self.retry_attempts),
            wait=self.wait_scenario,
            retry=retry_if_exception_type(
                (
                    httpx.DecodingError,
                    httpx.TransportError,
                    httpx.TooManyRedirects,
                    RetryableHTTPStatusError,
                )
            ),
            reraise=True,
        )
        async def make_request() -> httpx.Response:
            with self.circuit_breaker.context():
                response = await self.client.request(method, url, **kwargs)

                if response.status_code in self.retryable_status_codes:
                    raise RetryableHTTPStatusError(
                        f"Retryable status code: {response.status_code}"
                    )

                response.raise_for_status()
                return response

        return await make_request()

    async def aclose(self) -> None:
        await self.client.aclose()
