from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class SettingBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")


class AISettings(SettingBaseModel):
    openai_base_url: str = "https://openrouter.ai/api/v1"
    "Base URL for OpenAI-compatible API"
    openai_api_key: SecretStr
    "API key for OpenAI-compatible API"
    openai_model: str = "openai/gpt-4o"
    "Model name for OpenAI-compatible API"
    temperature: float = 0.25
    "Temperature setting for OpenAI-compatible API"
    use_judge: bool = True  # Whether to use self-judging stage


class Settings(SettingBaseModel):
    """Settings for the application."""

    schema_: str = Field(None, alias="$schema")
    ai: AISettings
    "AI settings"

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path) as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w") as f:
            schema = {
                "$schema": "https://json-schema.org/draft-07/schema",
                **cls.model_json_schema(),
            }
            yaml.dump(schema, f, sort_keys=False)
