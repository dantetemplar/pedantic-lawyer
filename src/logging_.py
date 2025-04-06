__all__ = ["logger"]

import logging.config
import os
from pathlib import Path

import yaml

project_root = os.getcwd()


class RelativePathFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.relativePath = Path(record.pathname).relative_to(project_root)
        return True


with open(Path(__file__).parent.parent / "logging.yaml") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger("src")
logger.addFilter(RelativePathFilter())
