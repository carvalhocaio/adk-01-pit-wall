from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_model: str = Field(
        default="gemini-flash-latest", validation_alias="PIT_WALL_MODEL"
    )
    max_llm_calls: int = Field(
        default=6, ge=1, validation_alias="PIT_WALL_MAX_LLM_CALLS"
    )
    adk_max_llm_calls: int = Field(default=500, validation_alias="ADK_MAX_LLM_CALLS")
    use_enterprise: bool = Field(
        default=False, validation_alias="GOOGLE_GENAI_USE_ENTERPRISE"
    )
    google_api_key: SecretStr | None = Field(
        default=None, validation_alias="GOOGLE_API_KEY"
    )
    google_cloud_project: str | None = Field(
        default=None, validation_alias="GOOGLE_CLOUD_PROJECT"
    )

    @model_validator(mode="after")
    def require_backend_credentials(self) -> Self:
        if self.use_enterprise and not self.google_cloud_project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required when "
                "GOOGLE_GENAI_USE_ENTERPRISE is enabled"
            )
        if not self.use_enterprise and self.google_api_key is None:
            raise ValueError("GOOGLE_API_KEY is required for the Gemini API backend")
        return self

    @model_validator(mode="after")
    def keep_budget_below_adk_limit(self) -> Self:
        if 0 < self.adk_max_llm_calls <= self.max_llm_calls:
            raise ValueError(
                f"PIT_WALL_MAX_LLM_CALLS ({self.max_llm_calls}) must be lower than "
                f"ADK_MAX_LLM_CALLS ({self.adk_max_llm_calls}), otherwise ADK "
                "raises before the budget can answer the user"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
