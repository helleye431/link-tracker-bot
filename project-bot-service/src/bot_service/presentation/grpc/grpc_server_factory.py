import grpc

from bot_service.application.services.update_service import UpdateService
from bot_service.presentation.grpc.bot_updates_servicer import BotUpdatesServicer
from bot_service.presentation.grpc.contracts.own import bot_pb2_grpc


def build_grpc_server(
    update_service: UpdateService,
    host: str,
    port: int,
) -> grpc.aio.Server:
    server = grpc.aio.server()

    bot_pb2_grpc.add_BotUpdatesServiceServicer_to_server(
        BotUpdatesServicer(update_service),
        server,
    )

    server.add_insecure_port(f"{host}:{port}")
    return server
