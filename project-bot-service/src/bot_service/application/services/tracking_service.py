from bot_service.domain.models.link import Link
from bot_service.application.ports.scrapper_port import ScrapperPort
from pydantic import ValidationError, HttpUrl
from bot_service.application.exceptions.service_exceptions import (
    LinkNotFoundError,
    LinkAlreadyExistsError,
    LinkDomainNotSupported,
    LinkInvalidError,
    ChatNotFoundError,
    ServiceError,
)
from bot_service.application.exceptions.scrapper_exceptions import (
    ScrapperLinkNotFoundError,
    ScrapperBadRequestError,
    ScrapperLinkAlreadyExistsError,
    ScrapperChatNotFoundError,
    ScrapperChatAlreadyExistsError,
)


class TrackingService:
    """
    Сервис управления отслеживаемыми ссылками и чатами.

    Отвечает за:
    - регистрацию и удаление чатов;
    - валидацию ссылок;
    - добавление и удаление отслеживания;
    - получение списка отслеживаемых ссылок;
    - преобразование ошибок внешнего scrapper_service-сервиса
      в ошибки доменного уровня.
    """

    def __init__(self, scrapper: ScrapperPort, validated_domains: list[str]):
        self.scrapper = scrapper
        self.validated_domains = validated_domains

    async def register_chat(self, chat_id: int) -> None:
        try:
            await self.scrapper.register_chat(chat_id)
        except ScrapperChatAlreadyExistsError:
            return
        except ScrapperBadRequestError:
            raise ServiceError
        except Exception:
            raise ServiceError

    async def delete_chat(self, chat_id: int) -> None:
        try:
            await self.scrapper.delete_chat(chat_id)
        except ScrapperChatNotFoundError:
            raise ChatNotFoundError(chat_id)
        except ScrapperBadRequestError:
            raise ServiceError
        except Exception:
            raise ServiceError

    async def validate_url(self, url: str) -> HttpUrl:
        try:
            validated_url = HttpUrl(url)
            if validated_url.host not in self.validated_domains:
                raise LinkDomainNotSupported(url)
        except ValidationError:
            raise LinkInvalidError(url)
        else:
            return validated_url

    async def check_exists_link(self, chat_id, url: HttpUrl) -> None:
        links = await self.get_list_links(chat_id)

        for link in links:
            if str(link.url) == str(url):
                raise LinkAlreadyExistsError(str(url))

    async def validate_new_link(self, chat_id: int, url: str) -> HttpUrl:
        """
        Валидирует новую ссылку перед добавлением в отслеживание.

        Проверяет:
        - корректность URL;
        - отсутствие такой ссылки среди уже отслеживаемых для данного чата.

        Возвращает валидированный HttpUrl.
        """

        validated_url = await self.validate_url(url)
        await self.check_exists_link(chat_id, validated_url)

        return validated_url

    async def track_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> None:

        link = Link(url=url, tags=tags, filters=filters)

        try:
            await self.scrapper.add_link(chat_id, link)
        except ScrapperChatNotFoundError:
            raise ChatNotFoundError(chat_id)
        except ScrapperLinkAlreadyExistsError:
            raise LinkAlreadyExistsError(str(url))
        except ScrapperBadRequestError:
            raise ServiceError
        except Exception:
            raise ServiceError

    async def untrack_link(self, chat_id: int, url: str) -> None:
        try:
            validated_url = await self.validate_url(url)
            await self.scrapper.remove_link(chat_id, validated_url)
        except LinkInvalidError:
            raise
        except ScrapperLinkNotFoundError:
            raise LinkNotFoundError(url)
        except ScrapperBadRequestError:
            raise ServiceError
        except Exception:
            raise ServiceError

    async def get_list_links(self, chat_id: int, tag: str | None = None) -> list[Link]:
        try:
            ans = await self.scrapper.get_links(chat_id)
        except ScrapperChatNotFoundError:
            raise ChatNotFoundError(chat_id)
        except ScrapperBadRequestError:
            raise ServiceError
        except Exception:
            raise ServiceError
        if tag:
            ans = [link for link in ans if tag in link.tags]
        return ans
