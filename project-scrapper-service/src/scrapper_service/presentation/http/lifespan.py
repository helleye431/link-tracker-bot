from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter

from scrapper_service.application.services.tracking_service import TrackingService


def build_lifespan(tracking_service: TrackingService, limiter: Limiter):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.tracking_service = tracking_service
        app.state.limiter = limiter
        yield

    return lifespan
