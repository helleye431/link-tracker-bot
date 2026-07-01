from fastapi import FastAPI
from slowapi import Limiter

from bot_service.application.services.update_service import UpdateService
from contextlib import asynccontextmanager


def build_lifespan(update_service: UpdateService, limiter: Limiter):

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.update_service = update_service
        app.state.limiter = limiter
        yield

    return lifespan
