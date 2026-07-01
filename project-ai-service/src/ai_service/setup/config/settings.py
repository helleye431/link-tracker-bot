from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
YAML_CONFIG_PATH = BASE_DIR / "processing_config.yml"


class FilteringSettings(BaseModel):
    stop_words: list[str] = Field(default_factory=list, alias="stop-words")
    excluded_authors: list[str] = Field(default_factory=list, alias="excluded-authors")
    min_length: int = Field(default=1, alias="min-length")


class SummarizationSettings(BaseModel):
    threshold: int = 200


class GroupingSettings(BaseModel):
    window_ms: int = Field(default=3000, alias="window-ms")


class PrioritizationSettings(BaseModel):
    high_keywords: list[str] = Field(default_factory=list, alias="high-keywords")
    low_keywords: list[str] = Field(default_factory=list, alias="low-keywords")


class AiAgentSettings(BaseModel):
    processing_model: str = Field(default="", alias="processing-model")
    filtering: FilteringSettings = Field(default_factory=FilteringSettings)
    summarization: SummarizationSettings = Field(default_factory=SummarizationSettings)
    grouping: GroupingSettings = Field(default_factory=GroupingSettings)
    prioritization: PrioritizationSettings = Field(
        default_factory=PrioritizationSettings
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=YAML_CONFIG_PATH,
        extra="ignore",
        populate_by_name=True,
    )

    ai_token: SecretStr = SecretStr("")

    kafka_bootstrap_servers: str = ""
    kafka_updates_consumer_group: str = ""
    kafka_auto_offset_reset: str = ""
    kafka_enable_auto_commit: bool = False
    kafka_processed_updates_topic: str = ""
    kafka_raw_updates_topic: str = ""
    kafka_raw_updates_dlq_topic: str = ""
    kafka_max_processing_retries: int = 0

    schema_registry_url: str = ""

    ai_agent: AiAgentSettings = Field(
        default_factory=AiAgentSettings,
        alias="ai-agent",
    )

    @property
    def ai_agent_processing_model(self) -> str:
        return self.ai_agent.processing_model

    @property
    def ai_agent_filtering_stop_words(self) -> list[str]:
        return self.ai_agent.filtering.stop_words

    @property
    def ai_agent_filtering_excluded_authors(self) -> list[str]:
        return self.ai_agent.filtering.excluded_authors

    @property
    def ai_agent_filtering_min_length(self) -> int:
        return self.ai_agent.filtering.min_length

    @property
    def ai_agent_summarization_threshold(self) -> int:
        return self.ai_agent.summarization.threshold

    @property
    def ai_agent_prioritization_low_keywords(self) -> list[str]:
        return self.ai_agent.prioritization.low_keywords

    @property
    def ai_agent_prioritization_high_keywords(self) -> list[str]:
        return self.ai_agent.prioritization.high_keywords

    @property
    def ai_agent_grouping_window_ms(self) -> int:
        return self.ai_agent.grouping.window_ms

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
