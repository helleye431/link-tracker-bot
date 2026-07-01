from pydantic import ValidationError
import structlog

from scrapper_service.application.exceptions.chat_exceptions import (
    ChatAlreadyExistsError,
    ChatNotFoundError,
)
from scrapper_service.application.exceptions.link_exceptions import (
    LinkAlreadyExistsError,
    LinkNotFoundError,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.presentation.grpc.contracts.own import (
    scrapper_pb2,
    scrapper_pb2_grpc,
)


logger = structlog.get_logger(__name__)


def build_error(
    description: str,
    code: str,
    exc: Exception | None = None,
) -> scrapper_pb2.ApiErrorResponse:
    return scrapper_pb2.ApiErrorResponse(
        description=description,
        code=code,
        exceptionName=exc.__class__.__name__ if exc else "",
        exceptionMessage=str(exc) if exc else "",
        stacktrace=[],
    )


def build_link_response(link) -> scrapper_pb2.LinkResponse:
    return scrapper_pb2.LinkResponse(
        id=link.id,
        url=str(link.url),
        tags=link.tags,
        filters=link.filters,
        last_seen_update=(
            link.last_seen_update.isoformat() if link.last_seen_update else ""
        ),
    )


class ScrapperServicer(scrapper_pb2_grpc.ScrapperServiceServicer):
    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    async def RegisterChat(self, request, context):
        logger.info(
            "register_chat_called",
            method="RegisterChat",
            chat_id=request.chat_id,
        )

        try:
            await self.tracking_service.register_chat(request.chat_id)
            logger.info(
                "register_chat_succeeded",
                method="RegisterChat",
                chat_id=request.chat_id,
            )
            return scrapper_pb2.RegisterChatResult(data=scrapper_pb2.EmptyData())

        except ChatAlreadyExistsError as exc:
            logger.warning(
                "register_chat_failed_chat_already_exists",
                method="RegisterChat",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.RegisterChatResult(
                error=build_error(
                    "Чат уже существует",
                    "CHAT_ALREADY_EXISTS",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "register_chat_failed_unexpected",
                method="RegisterChat",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.RegisterChatResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )

    async def DeleteChat(self, request, context):
        logger.info(
            "delete_chat_called",
            method="DeleteChat",
            chat_id=request.chat_id,
        )

        try:
            await self.tracking_service.delete_chat(request.chat_id)
            logger.info(
                "delete_chat_succeeded",
                method="DeleteChat",
                chat_id=request.chat_id,
            )
            return scrapper_pb2.DeleteChatResult(data=scrapper_pb2.EmptyData())

        except ChatNotFoundError as exc:
            logger.warning(
                "delete_chat_failed_chat_not_found",
                method="DeleteChat",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.DeleteChatResult(
                error=build_error(
                    "Чат не существует",
                    "CHAT_NOT_FOUND",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "delete_chat_failed_unexpected",
                method="DeleteChat",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.DeleteChatResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )

    async def GetLinks(self, request, context):
        logger.info(
            "get_links_called",
            method="GetLinks",
            chat_id=request.chat_id,
        )

        try:
            links = await self.tracking_service.get_links(request.chat_id)
            logger.info(
                "get_links_succeeded",
                method="GetLinks",
                chat_id=request.chat_id,
                links_count=len(links),
            )
            return scrapper_pb2.GetLinksResult(
                data=scrapper_pb2.ListLinksResponse(
                    links=[build_link_response(link) for link in links],
                    size=len(links),
                )
            )

        except ChatNotFoundError as exc:
            logger.warning(
                "get_links_failed_chat_not_found",
                method="GetLinks",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.GetLinksResult(
                error=build_error(
                    "Чат не существует",
                    "CHAT_NOT_FOUND",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "get_links_failed_unexpected",
                method="GetLinks",
                chat_id=request.chat_id,
                error=str(exc),
            )
            return scrapper_pb2.GetLinksResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )

    async def AddLink(self, request, context):
        logger.info(
            "add_link_called",
            method="AddLink",
            chat_id=request.chat_id,
            link=request.link,
            tags=list(request.tags),
            filters=list(request.filters),
        )

        try:
            created_link = await self.tracking_service.add_link(
                chat_id=request.chat_id,
                url=request.link,
                tags=list(request.tags),
                filters=list(request.filters),
            )
            logger.info(
                "add_link_succeeded",
                method="AddLink",
                chat_id=request.chat_id,
                link_id=created_link.id,
                url=str(created_link.url),
            )
            return scrapper_pb2.AddLinkResult(data=build_link_response(created_link))

        except ChatNotFoundError as exc:
            logger.warning(
                "add_link_failed_chat_not_found",
                method="AddLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.AddLinkResult(
                error=build_error(
                    "Чат не существует",
                    "CHAT_NOT_FOUND",
                    exc,
                )
            )

        except LinkAlreadyExistsError as exc:
            logger.warning(
                "add_link_failed_link_already_exists",
                method="AddLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.AddLinkResult(
                error=build_error(
                    "Ссылка уже отслеживается",
                    "LINK_ALREADY_EXISTS",
                    exc,
                )
            )

        except ValidationError as exc:
            logger.warning(
                "add_link_failed_validation_error",
                method="AddLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.AddLinkResult(
                error=build_error(
                    "Некорректные параметры запроса",
                    "BAD_REQUEST",
                    exc,
                )
            )

        except ValueError as exc:
            logger.warning(
                "add_link_failed_bad_request",
                method="AddLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.AddLinkResult(
                error=build_error(
                    "Некорректные параметры запроса",
                    "BAD_REQUEST",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "add_link_failed_unexpected",
                method="AddLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.AddLinkResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )

    async def RemoveLink(self, request, context):
        logger.info(
            "remove_link_called",
            method="RemoveLink",
            chat_id=request.chat_id,
            link=request.link,
        )

        try:
            removed_link = await self.tracking_service.remove_link(
                chat_id=request.chat_id,
                url=request.link,
            )
            logger.info(
                "remove_link_succeeded",
                method="RemoveLink",
                chat_id=request.chat_id,
                link_id=removed_link.id,
                url=str(removed_link.url),
            )
            return scrapper_pb2.RemoveLinkResult(data=build_link_response(removed_link))

        except ChatNotFoundError as exc:
            logger.warning(
                "remove_link_failed_chat_not_found",
                method="RemoveLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.RemoveLinkResult(
                error=build_error(
                    "Чат не существует или ссылка не найдена",
                    "CHAT_NOT_FOUND",
                    exc,
                )
            )

        except LinkNotFoundError as exc:
            logger.warning(
                "remove_link_failed_link_not_found",
                method="RemoveLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.RemoveLinkResult(
                error=build_error(
                    "Ссылки не существует",
                    "LINK_NOT_FOUND",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "remove_link_failed_unexpected",
                method="RemoveLink",
                chat_id=request.chat_id,
                link=request.link,
                error=str(exc),
            )
            return scrapper_pb2.RemoveLinkResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )
