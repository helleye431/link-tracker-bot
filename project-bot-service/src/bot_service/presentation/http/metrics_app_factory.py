from fastapi import FastAPI
from prometheusrock import metrics_route


def create_metrics_app() -> FastAPI:
    app = FastAPI(title="bot-service-metrics")
    app.add_route("/metrics", metrics_route)
    return app
