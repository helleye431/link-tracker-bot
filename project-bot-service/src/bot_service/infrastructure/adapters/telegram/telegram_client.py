from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.filters import Command
from pydantic import SecretStr
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot_service.application.ports.telegram_port import TelegramPort
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers_provider import (
    HandlersProvider,
)
from bot_service.infrastructure.adapters.telegram.filters.unknown_command import (
    UnknownCommandFilter,
)
import structlog
from time import perf_counter
from bot_service.infrastructure.observability.metrics import (
    command_requests_total,
    command_duration_ms_total,
    sent_notification_total,
)


logger = structlog.get_logger(__name__)


def observe_command(handler):
    """
    Функция-обёртка для сбора метрик с хэндлеров
    """

    async def wrapped(message: Message, state: FSMContext):
        if isinstance(handler, CommandHandler):
            command = f"/{handler.name}"
        else:
            command = f"fsm:{handler.__class__.__name__}"

        command_requests_total.labels(command=command).inc()

        started_at = perf_counter()
        try:
            await handler.handle(message, state)
        finally:
            command_duration_ms_total.labels(
                scope="bot_command",
                scope_type=command,
            ).observe((perf_counter() - started_at) * 1000)

    return wrapped


class TelegramClient(TelegramPort):
    """
    Класс-адаптер для работы с Telegram API и aiogram.

    Отвечает за:
    - регистрацию handler'ов
    - специфичную отправку сообщений
    - настройку меню команд в боте
    - запуск polling
    """

    def __init__(self, token: SecretStr, handlers_provider: HandlersProvider):
        self.bot = Bot(token=token.get_secret_value())
        self.dp = Dispatcher()
        self.handlers_provider = handlers_provider

    async def register_handlers(self) -> None:
        """Регистрация всех обработчиков сообщений."""

        for handler in self.handlers_provider.command_handlers:
            self.dp.message.register(
                observe_command(handler),
                Command(handler.name),
            )

        # отдельная регистрация неизвестных команд по фильтру
        self.dp.message.register(
            observe_command(self.handlers_provider.unknown_handler),
            UnknownCommandFilter(self.handlers_provider.handlers_names),
        )

        # регистрация handler-ов машины состояний по их состояниям
        for handler in self.handlers_provider.fsm_handlers:
            self.dp.message.register(observe_command(handler), handler.state)
        logger.info("commands registered")

    async def register_error_handler(self) -> None:
        """Глобальная обработка ошибок всех handler'ов."""

        @self.dp.errors()
        async def global_error_handler(event):
            logger.exception("handler failed", error=event.exception)

            if event.update.message:
                await event.update.message.answer("Произошла ошибка. Попробуйте позже.")

        logger.info("error handler registered")

    async def send_message(self, chat_id: int, message: str) -> None:
        await self.bot.send_message(chat_id, message)
        sent_notification_total.inc()

    async def setup_menu(self) -> None:
        """Регистрация команд в меню Telegram."""

        await self.bot.set_my_commands(
            [
                BotCommand(command=handler.name, description=handler.description)
                for handler in self.handlers_provider.command_handlers
            ]
        )

        logger.info("telegram command panel registered")

    async def run(self) -> None:
        """Старт бота"""

        await self.register_handlers()
        await self.setup_menu()
        await self.register_error_handler()
        logger.info("polling start")
        await self.dp.start_polling(self.bot)

    async def shutdown(self) -> None:
        await self.bot.session.close()
