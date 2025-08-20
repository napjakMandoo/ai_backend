import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.crawler.ai.jsonSchema import Preferential
from src.crawler.ai.preprocessPrompt import SYS_RULE
import time
import random
import logging
from typing import Optional
from google.genai.errors import ServerError, APIError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

class LlmUtil:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")

        if not api_key:
            raise RuntimeError("GENAI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)
        self.req_timeout_sec = 60
        self.max_retry = 6
        self.max_backoff_sec = 60


    def _gen_once(self, model: str, prompt: str, config):
        return self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

    def _gen_with_retry(self, model: str, prompt: str, config):
        delay = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retry + 1):
            try:
                self.logger.info(f"{model} 시도 ({attempt}/{self.max_retry})")
                resp = self._gen_once(model, prompt, config)
                self.logger.info(f"{model} 성공")
                return resp
            except (ServerError, APIError) as e:
                code = getattr(e, "status_code", None)
                retryable = (code in RETRYABLE_STATUS)
                self.logger.warning(f"{model} 시도 {attempt} 실패: {code} {e}")

                if not retryable or attempt == self.max_retry:
                    last_exc = e
                    break

                wait = min(self.max_backoff_sec, delay) + random.uniform(0, delay/2)
                self.logger.warning(f"{model} 재시도 대기 {wait:.1f}s (code={code})")
                time.sleep(wait)
                delay *= 2
                continue
            except Exception as e:
                last_exc = e
                self.logger.error(f"{model} 예기치 못한 예외: {e}")
                break

        if last_exc:
            raise last_exc
        raise RuntimeError(f"{model} 재시도 실패(원인 미상)")

    def create_preferential_json(self, content: str) -> "Preferential":
        prompt = f"{SYS_RULE}{content}"
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Preferential,
        )

        self.logger.info("상품 하나 전처리 시작")

        response = None
        last_err = None

        for model in ("gemini-2.5-flash", "gemini-2.5-pro"):
            try:
                response = self._gen_with_retry(model, prompt, config)
                break
            except Exception as e:
                last_err = e
                self.logger.error(f"{model} 최종 실패: {e}")
                continue

        if response is None:
            raise RuntimeError(f"모든 모델 실패. 마지막 에러: {last_err}")

        try:
            parsed: Preferential = response.parsed
            self.logger.info("상품 하나 전처리 완료")
            return parsed
        except Exception as e:
            self.logger.error(f"응답 파싱 실패: {e}")
            raise ValueError(f"API 응답 파싱 실패: {e}") from e