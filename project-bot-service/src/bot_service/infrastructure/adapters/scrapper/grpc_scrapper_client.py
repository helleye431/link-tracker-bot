from datetime import datetime
import grpc
import structlog
from pydantic import HttpUrl

from bot_service.application.exceptions.scrapper_exceptions import (
    ScrapperBadRequestError,
    ScrapperChatAlreadyExistsError,
    ScrapperChatNotFoundError,
    ScrapperLinkAlreadyExistsError,
    ScrapperLinkNotFoundError,
)
from bot_service.domain.models.link import Link
from bot_service.application.ports.scrapper_port import ScrapperPort
from bot_service.presentation.grpc.contracts.external import (
    scrapper_pb2,
    scrapper_pb2_grpc,
)

logger = structlog.get_logger(__name__)


class GrpcScrapperClient(ScrapperPort):
    """
    gRPC-адаптер для взаимодействия с внешним scrapper_service-сервисом.
    Обрабатывает ответы от сервиса и
    преобразует коды ошибок во внутренние исключения приложения.
    """

    def __init__(self, target: str):
        self.target = target
        self.channel = grpc.aio.insecure_channel(target)
        self.stub = scrapper_pb2_grpc.ScrapperServiceStub(self.channel)

    async def register_chat(self, chat_id: int) -> None:
        try:
            response = await self.stub.RegisterChat(
                scrapper_pb2.RegisterChatRequest(chat_id=chat_id),
                timeout=5,
            )
        except grpc.aio.AioRpcError as exc:
            logger.warning(
                "grpc_scrapper_register_chat_failed",
                target=self.target,
                chat_id=chat_id,
                status_code=exc.code().name,
                details=exc.details(),
            )
            raise RuntimeError(
                f"gRPC register_chat failed: {exc.code().name} - {exc.details()}"
            ) from exc

        if response.HasField("error"):
            logger.warning(
                "grpc_scrapper_register_chat_failed",
                target=self.target,
                chat_id=chat_id,
                code=response.error.code,
                description=response.error.description,
            )
            match response.error.code:
                case "BAD_REQUEST":
                    raise ScrapperBadRequestError()
                case "CHAT_ALREADY_EXISTS":
                    raise ScrapperChatAlreadyExistsError()
                case _:
                    raise RuntimeError(
                        response.error.exceptionMessage or response.error.description
                    )

        logger.info(
            "grpc_scrapper_register_chat_succeeded",
            target=self.target,
            chat_id=chat_id,
        )

    async def delete_chat(self, chat_id: int) -> None:
        try:
            response = await self.stub.DeleteChat(
                scrapper_pb2.DeleteChatRequest(chat_id=chat_id),
                timeout=5,
            )
        except grpc.aio.AioRpcError as exc:
            logger.warning(
                "grpc_scrapper_delete_chat_failed",
                target=self.target,
                chat_id=chat_id,
                status_code=exc.code().name,
                details=exc.details(),
            )
            raise RuntimeError(
                f"gRPC delete_chat failed: {exc.code().name} - {exc.details()}"
            ) from exc

        if response.HasField("error"):
            logger.warning(
                "grpc_scrapper_delete_chat_failed",
                target=self.target,
                chat_id=chat_id,
                code=response.error.code,
                description=response.error.description,
            )
            match response.error.code:
                case "BAD_REQUEST":
                    raise ScrapperBadRequestError()
                case "CHAT_NOT_FOUND":
                    raise ScrapperChatNotFoundError()
                case _:
                    raise RuntimeError(
                        response.error.exceptionMessage or response.error.description
                    )

        logger.info(
            "grpc_scrapper_delete_chat_succeeded",
            target=self.target,
            chat_id=chat_id,
        )

    async def add_link(self, chat_id: int, link: Link) -> None:
        try:
            response = await self.stub.AddLink(
                scrapper_pb2.AddLinkRequest(
                    chat_id=chat_id,
                    link=str(link.url),
                    tags=link.tags,
                    filters=link.filters,
                ),
                timeout=5,
            )
        except grpc.aio.AioRpcError as exc:
            logger.warning(
                "grpc_scrapper_add_link_failed",
                target=self.target,
                chat_id=chat_id,
                url=str(link.url),
                status_code=exc.code().name,
                details=exc.details(),
            )
            raise RuntimeError(
                f"gRPC add_link failed: {exc.code().name} - {exc.details()}"
            ) from exc

        if response.HasField("error"):
            logger.warning(
                "grpc_scrapper_add_link_failed",
                target=self.target,
                chat_id=chat_id,
                url=str(link.url),
                code=response.error.code,
                description=response.error.description,
            )
            match response.error.code:
                case "BAD_REQUEST":
                    raise ScrapperBadRequestError()
                case "CHAT_NOT_FOUND":
                    raise ScrapperChatNotFoundError()
                case "LINK_ALREADY_EXISTS":
                    raise ScrapperLinkAlreadyExistsError()
                case _:
                    raise RuntimeError(
                        response.error.exceptionMessage or response.error.description
                    )

        logger.info(
            "grpc_scrapper_add_link_succeeded",
            target=self.target,
            chat_id=chat_id,
            url=str(link.url),
        )

    async def remove_link(self, chat_id: int, url: HttpUrl) -> None:
        try:
            response = await self.stub.RemoveLink(
                scrapper_pb2.RemoveLinkRequest(
                    chat_id=chat_id,
                    link=str(url),
                ),
                timeout=5,
            )
        except grpc.aio.AioRpcError as exc:
            logger.warning(
                "grpc_scrapper_remove_link_failed",
                target=self.target,
                chat_id=chat_id,
                url=str(url),
                status_code=exc.code().name,
                details=exc.details(),
            )
            raise RuntimeError(
                f"gRPC remove_link failed: {exc.code().name} - {exc.details()}"
            ) from exc

        if response.HasField("error"):
            logger.warning(
                "grpc_scrapper_remove_link_failed",
                target=self.target,
                chat_id=chat_id,
                url=str(url),
                code=response.error.code,
                description=response.error.description,
            )
            match response.error.code:
                case "BAD_REQUEST":
                    raise ScrapperBadRequestError()
                case "LINK_NOT_FOUND":
                    raise ScrapperLinkNotFoundError()
                case "CHAT_NOT_FOUND":
                    raise ScrapperChatNotFoundError()
                case _:
                    raise RuntimeError(
                        response.error.exceptionMessage or response.error.description
                    )

        logger.info(
            "grpc_scrapper_remove_link_succeeded",
            target=self.target,
            chat_id=chat_id,
            url=str(url),
        )

    async def get_links(self, chat_id: int) -> list[Link] | None:
        try:
            response = await self.stub.GetLinks(
                scrapper_pb2.GetLinksRequest(chat_id=chat_id),
                timeout=5,
            )
        except grpc.aio.AioRpcError as exc:
            logger.warning(
                "grpc_scrapper_get_links_failed",
                target=self.target,
                chat_id=chat_id,
                status_code=exc.code().name,
                details=exc.details(),
            )
            raise RuntimeError(
                f"gRPC get_links failed: {exc.code().name} - {exc.details()}"
            ) from exc

        if response.HasField("error"):
            logger.warning(
                "grpc_scrapper_get_links_failed",
                target=self.target,
                chat_id=chat_id,
                code=response.error.code,
                description=response.error.description,
            )
            match response.error.code:
                case "BAD_REQUEST":
                    raise ScrapperBadRequestError()
                case "CHAT_NOT_FOUND":
                    raise ScrapperChatNotFoundError()
                case _:
                    raise RuntimeError(
                        response.error.exceptionMessage or response.error.description
                    )

        result = []
        for item in response.data.links:
            last_seen_update = None
            if item.last_seen_update:
                last_seen_update = datetime.fromisoformat(item.last_seen_update)

            result.append(
                Link(
                    id=item.id,
                    url=item.url,
                    tags=list(item.tags),
                    filters=list(item.filters),
                    last_seen_update=last_seen_update,
                )
            )

        logger.info(
            "grpc_scrapper_get_links_succeeded",
            target=self.target,
            chat_id=chat_id,
            links_count=len(result),
        )

        return result

    async def aclose(self) -> None:
        await self.channel.close()
        logger.info("grpc_scrapper_client_closed", target=self.target)
