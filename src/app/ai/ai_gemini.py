import logging
import os
import time
import random
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

from src.app.ai.prompt_eng import PROMPT_ENG
from src.app.dto.response.response_ai_dto import response_ai_dto


class ai_gemini:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing AI recommendation service")

        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")
        if not api_key:
            self.logger.error("GENAI_API_KEY environment variable is not set")
            raise RuntimeError("GENAI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.logger.info("GenAI client initialized successfully")

    def create_response(self, content: dict, model:str) -> response_ai_dto | ValueError:
        self.logger.info("Starting AI recommendation generation")

        content_json = json.dumps(content, ensure_ascii=False)
        prompt_length = len(content_json)
        self.logger.info(f"Content prepared for AI: {prompt_length} characters")

        prompt = f"{PROMPT_ENG}{content_json}"
        full_prompt_length = len(prompt)
        self.logger.debug(f"Full prompt prepared: {full_prompt_length} characters total")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_ai_dto,
        )
        self.logger.debug("AI generation config set: JSON response with schema validation")

        max_retry = 5
        for attempt in range(1, max_retry + 1):
            try:
                self.logger.info(f"Attempting AI generation (attempt {attempt}/{max_retry})")
                start_time = time.time()

                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )

                processing_time = time.time() - start_time
                self.logger.info(f"AI generation successful in {processing_time:.2f} seconds")
                break

            except ServerError as e:
                if getattr(e, "status_code", None) == 503 and attempt < max_retry:
                    wait = min(60, 2 ** (attempt - 1)) + random.random()
                    self.logger.warning(f"AI model overloaded (503). Retry {attempt}/{max_retry} after {wait:.1f}s")
                    time.sleep(wait)
                    continue
                else:
                    self.logger.error(f"AI server error on attempt {attempt}: {str(e)}")
                    raise
            except Exception as e:
                self.logger.error(f"Unexpected error during AI generation on attempt {attempt}: {str(e)}")
                if attempt == max_retry:
                    raise
                continue

        self.logger.info(f"AI Raw Response: {response.text}")  # AI 원본 응답 출력
        try:
            if hasattr(response, 'text') and response.text:
                self.logger.info(f"AI Raw Response (text): {response.text}")
            elif hasattr(response, 'candidates') and response.candidates:
                content = response.candidates[0].content.parts[0].text
                self.logger.info(f"AI Raw Response (candidates): {content}")
            else:
                self.logger.info(f"AI Raw Response (full object): {response}")
                self.logger.info(f"AI Response attributes: {dir(response)}")
        except Exception as e:
            self.logger.error(f"Error accessing AI response: {e}")
            self.logger.info(f"AI Response type: {type(response)}")

        try:
            parsed: response_ai_dto = response.parsed
            combinations_count = len(parsed.combination) if parsed and parsed.combination else 0
            self.logger.info(f"AI response parsed successfully: {combinations_count} combinations generated")

            if parsed and parsed.combination:
                total_payment = parsed.total_payment
                period_months = parsed.period_months
                self.logger.info(
                    f"Recommendation summary: total_payment={total_payment}, period={period_months} months")

            return parsed

        except Exception as e:
            self.logger.error(f"Error parsing AI response: {str(e)}")
            raise