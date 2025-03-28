import os
from pathlib import Path

import yaml

from src.config_schema import Settings

settings_path = os.getenv("SETTINGS_PATH", None)
if settings_path is None:
    settings_path = Path(__file__).parent.parent / "settings.yaml"
else:
    settings_path = Path(settings_path)
settings: Settings = Settings.from_yaml(settings_path)


with (Path(__file__).parent.parent / "prompts.yaml").open() as f:
    prompts = yaml.safe_load(f)
