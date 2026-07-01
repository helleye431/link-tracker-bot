from bot_service.application.ports.scrapper_port import ScrapperPort
from bot_service.infrastructure.adapters.scrapper.grpc_scrapper_client import (
    GrpcScrapperClient,
)
from bot_service.infrastructure.adapters.scrapper.http_scrapper_client import (
    HttpScrapperClient,
)
from bot_service.infrastructure.adapters.scrapper.utils.resilient_http_client import (
    ResilientHttpClient,
)


def build_scrapper_client(
    interservice_transport: str,
    scrapper_grpc_target: str,
    scrapper_url: str,
    timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: int,
    retry_enable_exponential_backoff: bool,
    retryable_status_codes: list[int],
    circuit_error_ratio: float,
    circuit_response_time: int,
    circuit_recovery_time: int,
    circuit_broken_time: int,
) -> ScrapperPort:
    match interservice_transport:
        case "grpc":
            return GrpcScrapperClient(scrapper_grpc_target)
        case "http":
            resilient_client = ResilientHttpClient(
                timeout_seconds=timeout_seconds,
                retry_attempts=retry_attempts,
                retry_backoff_seconds=retry_backoff_seconds,
                retry_enable_exponential_backoff=retry_enable_exponential_backoff,
                retryable_status_codes=retryable_status_codes,
                circuit_error_ratio=circuit_error_ratio,
                circuit_response_time=circuit_response_time,
                circuit_broken_time=circuit_broken_time,
                circuit_recovery_time=circuit_recovery_time,
            )
            return HttpScrapperClient(scrapper_url, client=resilient_client)
        case _:
            raise ValueError(
                f"Такого вида транспорта не существует {interservice_transport}"
            )
