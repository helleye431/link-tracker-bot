from typing import Literal
from ai_service.domain.models.processed_update import ProcessedUpdate
from ai_service.domain.models.raw_update import RawUpdate
from ai_service.application.ports.update_processor_port import UpdateProcessorPort

import httpx
import structlog
import re

logger = structlog.get_logger(__name__)


class AIProcessor(UpdateProcessorPort):
    def __init__(
        self,
        token: str,
        model: str,
        stop_words: list[str],
        excluded_authors: list[str],
        min_length: int,
        summarization_threshold: int,
        high_keywords: list[str],
        low_keywords: list[str],
    ):
        self.token = token
        self.model = model

        self.stop_words = {word.lower() for word in stop_words}
        self.excluded_authors = {author.lower() for author in excluded_authors}

        self.high_keywords = {keyword.lower() for keyword in high_keywords}
        self.low_keywords = {keyword.lower() for keyword in low_keywords}

        self.min_length = min_length
        self.summarization_threshold = summarization_threshold

        self.base_url = "https://router.huggingface.co/v1/chat/completions"
        self.client = httpx.AsyncClient(timeout=60)

    async def process_update(self, update: RawUpdate) -> ProcessedUpdate | None:

        # пропуск обработки, если в объекте обновления текст ошибки
        if update.is_error:
            return ProcessedUpdate(
                id=update.id,
                url=update.url,
                description=update.description,
                tgChatIds=update.tgChatIds,
                is_error=update.is_error,
                priority="MEDIUM",
            )

        description = update.description
        author = update.author
        filtering_text = self._filter_text(text=description, author=author)

        if filtering_text is None:
            return None

        priority = self._determine_priority(text=filtering_text)

        if len(filtering_text) > self.summarization_threshold:
            result_text = await self._summarize_text(text=filtering_text)
        else:
            result_text = filtering_text

        return ProcessedUpdate(
            id=update.id,
            url=update.url,
            description=result_text,
            tgChatIds=update.tgChatIds,
            is_error=update.is_error,
            priority=priority,
        )

    def _determine_priority(self, text: str) -> Literal["LOW", "MEDIUM", "HIGH"]:
        have_low_keywords = False
        for word in re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)?", text):
            word = word.lower()

            if word in self.high_keywords:
                return "HIGH"

            if word in self.low_keywords:
                have_low_keywords = True

        if have_low_keywords:
            return "LOW"

        return "MEDIUM"

    def _filter_text(self, text: str, author: str) -> str | None:
        if author.lower() in self.excluded_authors:
            return None

        if len(text) < self.min_length:
            return None

        for word in re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)?", text):
            word = word.lower()

            if word in self.stop_words:
                return None

        return text

    def _cut_text(self, text: str) -> str:
        return text[: self.summarization_threshold] + "..."

    async def _summarize_text(self, text: str) -> str:
        try:
            return await self._request_to_ai(text=text)
        except Exception:
            # обычная обрезка в случае неполадок AI API
            return self._cut_text(text)

    async def _request_to_ai(self, text: str) -> str:
        prompt = f"""
        Сделай краткое изложение основного текста, который идёт после поля «Время создания».
        
        Верни результат строго в формате:
        
        Произошли изменения по ссылке <ссылка>
        Событие: 
        Тема:
        Пользователь:
        Время создания:
        Превью:
        
        Правила:
        - Сохрани строку «Произошли изменения по ссылке <ссылка>», 
          значения полей «Событие» «Тема», «Пользователь», «Время создания» 
          без изменений.
        - Не изменяй порядок строк и названия полей.
        - В поле «Превью» напиши краткое изложение только основного текста,
          который идёт после поля «Время создания».
        - Превью должно быть не длиннее {self.summarization_threshold} символов.
        - Не добавляй пояснений, комментариев, Markdown-разметки и лишнего текста.
        - Если основной текст пустой или неинформативный, оставь поле «Превью» пустым.
        
        Текст для выполнения:
        {text}
        """

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = await self.client.post(
                url=self.base_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and "error" in data:
                raise RuntimeError(data["error"])

            try:
                result = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Unexpected response format: {data}") from exc

            if not isinstance(result, str) or not result.strip():
                raise RuntimeError(f"Empty AI response: {data}")

            return result.strip()

        except Exception as exc:
            logger.info(
                "api_client_has_any_error",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise

    async def aclose(self) -> None:
        await self.client.aclose()
