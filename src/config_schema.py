from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ImportString


class SettingBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")


class AISettings(SettingBaseModel):
    openai_base_url: str = "https://openrouter.ai/api/v1"
    "Base URL for OpenAI-compatible API"
    openai_api_key: SecretStr
    "API key for OpenAI-compatible API"
    openai_model: str = "google/gemini-2.0-flash-001"
    "Model name for OpenAI-compatible API"


class Settings(SettingBaseModel):
    """Settings for the application."""

    schema_: str = Field(None, alias="$schema")
    ai: AISettings
    "AI settings"
    parsing_pipeline: ImportString
    "Parsing pipeline for the application"

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path) as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w") as f:
            schema = {"$schema": "https://json-schema.org/draft-07/schema", **cls.model_json_schema()}
            yaml.dump(schema, f, sort_keys=False)
