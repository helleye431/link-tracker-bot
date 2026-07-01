from bot_service.infrastructure.adapters.telegram.handlers.command.help_handler import (
    HelpHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.list_handler import (
    ListHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.start_handler import (
    StartHandler,
)
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
from bot_service.infrastructure.adapters.telegram.handler_interfaces.fsm_handler import (
    FSMHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.unknown_handler import (
    UnknownHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.track_handler import (
    TrackHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_link_handler import (
    TrackLinkHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_tags_handler import (
    TrackTagsHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_filters_handler import (
    TrackFiltersHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.untrack_scenario.untrack_link_handler import (
    UntrackLinkHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.cancel_handler import (
    CancelHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.command.untrack_handler import (
    UntrackHandler,
)
from bot_service.application.services.tracking_service import TrackingService
import structlog

logger = structlog.get_logger(__name__)


class HandlersProvider:
    """
    Централизованный источник всех команд

    Нужен чтобы для сбора всех команд в одном месте и их удобного
    использования в коде
    """

    def __init__(self, tracking_service: TrackingService):

        help_handler = HelpHandler()
        self._command_handlers = [
            StartHandler(tracking_service),
            ListHandler(tracking_service),
            TrackHandler(),
            UntrackHandler(),
            CancelHandler(),
            help_handler,
        ]

        # добавление в help handler всех handler'ов для автоматической генерации сообщения
        help_handler.set_handlers(self._command_handlers)

        self._fsm_handlers = [
            TrackFiltersHandler(tracking_service),
            TrackLinkHandler(tracking_service),
            TrackTagsHandler(),
            UntrackLinkHandler(tracking_service),
        ]

        self._unknown_handler = UnknownHandler()

    @property
    def command_handlers(self) -> list[CommandHandler]:
        return self._command_handlers

    @property
    def fsm_handlers(self) -> list[FSMHandler]:
        return self._fsm_handlers

    @property
    def handlers_names(self) -> list[str]:
        return [handler.name for handler in self._command_handlers]

    @property
    def unknown_handler(self) -> UnknownHandler:
        return self._unknown_handler
