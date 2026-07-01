import grpc
from scrapper_service.presentation.grpc.contracts.own import scrapper_pb2_grpc
from scrapper_service.presentation.grpc.scrapper_servicer import ScrapperServicer
from scrapper_service.application.services.tracking_service import TrackingService


def build_grpc_server(
    tracking_service: TrackingService,
    host: str,
    port: int,
) -> grpc.aio.Server:
    server = grpc.aio.server()

    scrapper_pb2_grpc.add_ScrapperServiceServicer_to_server(
        ScrapperServicer(tracking_service),
        server,
    )

    server.add_insecure_port(f"{host}:{port}")
    return server
