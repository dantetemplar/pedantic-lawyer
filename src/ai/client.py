from openai import AsyncOpenAI, OpenAI

from src.config import settings
from src.logging_ import logger

logger.info("Initializing OpenAI client")

client = OpenAI(
    base_url=settings.ai.openai_base_url,
    api_key=settings.ai.openai_api_key.get_secret_value(),
)

async_client = AsyncOpenAI(
    base_url=settings.ai.openai_base_url,
    api_key=settings.ai.openai_api_key.get_secret_value(),
)
