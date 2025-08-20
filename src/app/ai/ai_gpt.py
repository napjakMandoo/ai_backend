from dotenv import load_dotenv
from openai import OpenAI
import json
from src.app.ai.prompt_eng import PROMPT_ENG
from src.app.dto.response.response_ai_dto import response_ai_dto

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

    def create_response(self, content: dict, model:str) -> response_ai_dto | ValueError:
        content_json = json.dumps(content, ensure_ascii=False)
        responses_parse = self.client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": PROMPT_ENG},
                {"role": "user", "content": content_json},
            ],
            text_format=response_ai_dto
        )

        return responses_parse.output_parsed
