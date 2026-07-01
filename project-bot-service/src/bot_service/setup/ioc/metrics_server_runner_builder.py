from bot_service.presentation.http.http_server_factory import build_http_server
from bot_service.presentation.http.http_server_runner import HttpServerRunner
from bot_service.presentation.http.metrics_app_factory import create_metrics_app


def build_metrics_server_runner(host: str, port: int):
    app = create_metrics_app()

    http_server = build_http_server(
        app=app,
        host=host,
        port=port,
    )

    return HttpServerRunner(http_server)
