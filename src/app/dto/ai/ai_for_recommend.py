import logging
import os
import time
import random

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

from src.app.dto.ai.prompt import PROMPT_ENG
from src.shared.ai.jsonSchema import Preferential
from src.app.dto.response.response_ai_dto import response_ai_dto


class ai_for_recommend:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")
        if not api_key:
            raise RuntimeError("GENAI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)

    def create_preferential_json(self, content: str) -> response_ai_dto | ValueError:

        prompt = f"{PROMPT_ENG}{content}"

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_ai_dto,
        )

        # 간단한 503 백오프 재시도 (필요시 제거 가능)
        max_retry = 5
        for attempt in range(1, max_retry + 1):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                break
            except ServerError as e:
                if getattr(e, "status_code", None) == 503 and attempt < max_retry:
                    wait = min(60, 2 ** (attempt - 1)) + random.random()
                    self.logger.warning(f"[503] model overloaded. retry {attempt}/{max_retry} after {wait:.1f}s")
                    time.sleep(wait)
                    continue
                raise

        parsed: response_ai_dto = response.parsed
        return parsed
