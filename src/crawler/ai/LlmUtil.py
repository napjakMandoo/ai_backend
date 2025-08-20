import logging
import os
import time
import random
import json
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from src.crawler.ai.jsonSchema import Preferential
from src.crawler.ai.preprocessPrompt import SYS_RULE


class LlmUtil:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")

        if not api_key:
            raise RuntimeError("GENAI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)

    def save_preferential_to_json(
            self,
            obj: Preferential,
            out_dir: str,
            filename: str | None = None,
            by_alias: bool = True,
            pretty: bool = True,
    ) -> str:

        Path(out_dir).mkdir(parents=True, exist_ok=True)

        # 파일명 자동 생성(가능하면 product_name 사용)
        def _slug(s: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)

        base = None
        for attr in ("product_name", "name", "title"):
            if hasattr(obj, attr) and getattr(obj, attr):
                base = str(getattr(obj, attr))
                break
        if not base:
            base = "preferential"

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{_slug(base)}_{ts}.json"
        if not filename.endswith(".json"):
            filename += ".json"

        if hasattr(obj, "model_dump"):  # pydantic v2
            data = obj.model_dump(by_alias=by_alias)
        else:  # pydantic v1
            data = obj.dict(by_alias=by_alias)

        json_str = json.dumps(
            data,
            ensure_ascii=False,
            indent=2 if pretty else None,
        )

        out_path = str(Path(out_dir, filename))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        self.logger.info(f"JSON saved: {out_path}")
        return out_path

    def create_preferential_json(self, content: str) -> Preferential:
        prompt = f"{SYS_RULE}{content}"

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Preferential,
        )

        self.logger.info("상품 하나 전처리 시작")

        max_retry = 6
        response = None

        for attempt in range(1, max_retry + 1):
            try:
                self.logger.info(f"gemini-2.5-flash 시도 ({attempt}/{max_retry})")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                self.logger.info("gemini-2.5-flash 성공")
                break

            except (ServerError, APIError) as e:
                self.logger.warning(f"gemini-2.5-flash 시도 {attempt} 실패: {e}")

                # 503 에러인 경우 재시도
                if hasattr(e, 'status_code') and e.status_code == 503:
                    if attempt < max_retry:
                        wait = min(60, 2 ** (attempt - 1)) + random.uniform(0, 1)
                        self.logger.warning(f"503 에러 - {wait:.1f}초 후 재시도")
                        time.sleep(wait)
                        continue
                    else:
                        self.logger.warning("gemini-2.5-flash 최대 재시도 횟수 초과")
                        break
                else:
                    self.logger.error(f"재시도 불가능한 에러: {e}")
                    break

            except Exception as e:
                self.logger.error(f"예상치 못한 에러: {e}")
                break

        if response is None:
            self.logger.warning("gemini-2.5-flash 실패, gemini-pro 전환")
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=prompt,
                    config=config,
                )
                self.logger.info("gemini-pro 성공")

            except Exception as e:
                self.logger.error(f"gemini-pro 실패: {e}")
                raise RuntimeError(f"모든 모델 실패. gemini-pro 에러: {e}") from e

        if response is None:
            raise RuntimeError("API 응답을 받지 못했습니다.")

        try:
            parsed: Preferential = response.parsed
            self.logger.info("상품 하나 전처리 완료")
        except Exception as e:
            self.logger.error(f"응답 파싱 실패: {e}")
            raise ValueError(f"API 응답 파싱 실패: {e}") from e

        try:
            self.save_preferential_to_json(
                obj=parsed,
                out_dir="./data/preferential",
                by_alias=True,
                pretty=True,
            )
        except Exception as e:
            self.logger.warning(f"JSON 저장 실패 (처리는 계속): {e}")

        return parsed