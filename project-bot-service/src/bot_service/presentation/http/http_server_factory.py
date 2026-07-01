import uvicorn
from fastapi import FastAPI


def build_http_server(app: FastAPI, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        reload=False,
    )
    return uvicorn.Server(config)
