from scrapper_service.presentation.grpc.grpc_server_factory import build_grpc_server
from scrapper_service.presentation.grpc.grpc_server_runner import GrpcServerRunner
from scrapper_service.presentation.http.http_server_factory import build_http_server
from scrapper_service.presentation.http.http_server_runner import HttpServerRunner
from scrapper_service.application.common.runners.base_runner import BaseRunner
from scrapper_service.application.services.tracking_service import TrackingService


def build_server_runner(
    interservice_transport: str,
    tracking_service: TrackingService,
    scrapper_grpc_host: str,
    scrapper_grpc_port: int,
    scrapper_http_host: str,
    scrapper_http_port: int,
    app,
) -> BaseRunner:
    match interservice_transport:
        case "grpc":
            grpc_server = build_grpc_server(
                tracking_service=tracking_service,
                host=scrapper_grpc_host,
                port=scrapper_grpc_port,
            )
            return GrpcServerRunner(grpc_server)

        case "http":
            http_server = build_http_server(
                app=app,
                host=scrapper_http_host,
                port=scrapper_http_port,
            )
            return HttpServerRunner(http_server)
        case _:
            raise ValueError(f"Неизвестный тип транспорта: {interservice_transport}")
