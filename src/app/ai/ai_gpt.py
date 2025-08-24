from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
import json
from src.app.ai.prompt_eng import PROMPT_ENG
from src.app.dto.response.response_ai_dto import response_ai_dto

import time
import logging
import os

class ai_gpt:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing AI recommendation service")

        load_dotenv()
        api_key = os.getenv("GPT_API_KEY")
        if not api_key:
            self.logger.error("GENAI_API_KEY environment variable is not set")
            raise RuntimeError("GENAI_API_KEY is not set.")

        self.client = OpenAI(api_key=api_key)
        self.logger.info("GenAI client initialized successfully")

    def create_response(self, content: dict, model: str):
        content_json = json.dumps(content, ensure_ascii=False)

        for attempt in range(5):  # 최대 5번 재시도
            try:
                responses_parse = self.client.responses.parse(
                    model=model,
                    input=[
                        {"role": "system", "content": PROMPT_ENG},
                        {"role": "user", "content": content_json},
                    ],
                    text_format=response_ai_dto,
                    max_output_tokens=2000
                )
                return responses_parse.output_parsed

            except RateLimitError as e:
                wait = 2 ** attempt
                self.logger.warning(f"Rate limit error, {wait}초 대기 후 재시도... ({attempt + 1}/5)")
                time.sleep(wait)

        raise RuntimeError("재시도 후에도 RateLimitError 발생")
