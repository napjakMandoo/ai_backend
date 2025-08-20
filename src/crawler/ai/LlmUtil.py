import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from google.generativeai.types import RequestOptions  # RequestOptions 임포트
from google.api_core.exceptions import ServerError

from src.crawler.ai.jsonSchema import Preferential  # Предполагается, что это ваш Pydantic DTO
import time
import random
import logging
from typing import Optional, Union  # Union 추가

from src.crawler.ai.preprocessPrompt import SYS_RULE

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LlmUtil:

    def __init__(self):
        self.SYS_RULE = SYS_RULE
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")

        if not api_key:
            self.logger.critical("GENAI_API_KEY environment variable is not set. Exiting.")
            raise RuntimeError("GENAI_API_KEY is not set. Please set the environment variable.")

        self.client = genai.Client(api_key=api_key)
        self.req_timeout_sec = 120  # 요청 타임아웃을 넉넉하게 120초로 설정
        self.max_retry = 6  # 총 시도 횟수 (1회 + 5회 재시도)
        self.max_backoff_sec = 60  # 최대 백오프 지연 시간

    def _gen_once(self, model: str, prompt: str, config: types.GenerateContentConfig):
        """
        단일 AI 모델 호출을 수행합니다.
        """
        # RequestOptions를 사용하여 timeout 설정
        return self.client.models.generate_content(
            model=model,
            contents=prompt,
            generation_config=config,  # API 문서에 따라 config 대신 generation_config 사용
            request_options=RequestOptions(timeout=self.req_timeout_sec)
        )

    def _gen_with_retry(self, model: str, prompt: str, config: types.GenerateContentConfig):
        """
        재시도 로직을 포함하여 AI 모델 호출을 수행합니다.
        """
        delay = 1.0  # 초기 재시도 지연 시간 (초)
        last_exc: Optional[Exception] = None  # 마지막으로 발생한 예외를 저장

        for attempt in range(1, self.max_retry + 1):
            try:
                self.logger.info(f"[{model}] 시도 ({attempt}/{self.max_retry})")
                resp = self._gen_once(model, prompt, config)
                self.logger.info(f"[{model}] 성공")
                return resp
            except (ServerError, APIError) as e:
                code = getattr(e, "status_code", None)
                retryable = (code in RETRYABLE_STATUS)
                self.logger.warning(f"[{model}] 시도 {attempt} 실패: 상태코드 {code} - {e}")

                if not retryable:  # 재시도 불가능한 오류인 경우
                    last_exc = e
                    self.logger.error(f"[{model}] 재시도 불가능한 오류({code}). 중단합니다.")
                    break

                if attempt == self.max_retry:  # 마지막 시도까지 실패한 경우
                    last_exc = e
                    self.logger.error(f"[{model}] 최대 재시도 횟수({self.max_retry}) 초과. 최종 실패.")
                    break

                # 재시도 가능한 오류 및 아직 최대 재시도 횟수에 도달하지 않은 경우
                wait = min(self.max_backoff_sec, delay + random.uniform(0, delay / 2))  # 지수 백오프 + 랜덤 지터
                self.logger.warning(f"[{model}] 재시도 대기 {wait:.1f}s (현재 지연: {delay:.1f}s, 코드: {code})")
                time.sleep(wait)
                delay *= 2  # 다음 재시도 지연 시간 두 배 증가
                continue  # 다음 재시도 시도
            except Exception as e:
                # ServerError, APIError 외의 예상치 못한 모든 예외
                last_exc = e
                self.logger.error(f"[{model}] 예기치 못한 예외 발생: {e}. 재시도하지 않고 중단합니다.")
                break  # 예상치 못한 예외는 즉시 중단

        # 모든 재시도 후에도 응답을 받지 못했거나 치명적인 오류가 발생한 경우 예외 발생
        if last_exc:
            raise last_exc  # 마지막으로 발생한 예외를 그대로 발생시킴
        # 이 라인에 도달하면 안 되지만, 혹시 모를 상황을 대비
        raise RuntimeError(f"[{model}] 재시도 후에도 응답을 받지 못했습니다 (원인 미상).")

    def create_preferential_json(self, content: str) -> "Preferential":
        """
        주어진 콘텐츠를 사용하여 AI 모델로부터 선호도 관련 JSON 응답을 생성합니다.
        flash 모델을 먼저 시도하고, 실패 시 pro 모델로 폴백합니다.
        """
        self.logger.info("상품 하나 전처리 시작")

        prompt = f"{self.SYS_RULE}{content}"  # SYS_RULE이 self에 속하는지 확인 필요, 아니면 전역 변수로 접근

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Preferential,  # Pydantic DTO 스키마 전달
            )
            self.logger.debug("AI generation config 설정 완료: JSON 응답 및 스키마 유효성 검사")
        except Exception as e:
            self.logger.error(f"GenerateContentConfig 설정 중 오류 발생: {e}")
            raise RuntimeError(f"AI 모델 설정 오류: {e}") from e

        response = None
        last_err: Optional[Exception] = None

        # 모델 우선순위: flash -> pro
        for model_name in ("gemini-2.5-flash", "gemini-2.5-pro"):
            try:
                self.logger.info(f"{model_name} 모델로 요청 시도.")
                response = self._gen_with_retry(model_name, prompt, config)
                self.logger.info(f"{model_name} 모델로부터 성공적으로 응답을 받았습니다.")
                break  # 성공하면 다른 모델 시도하지 않고 루프 탈출
            except Exception as e:
                last_err = e
                self.logger.error(f"{model_name} 모델 최종 실패: {e}")
                # 다음 모델로 시도하기 위해 continue

        if response is None:
            # 모든 모델이 실패한 경우
            error_message = f"모든 AI 모델({', '.join(['gemini-2.5-flash', 'gemini-2.5-pro'])})이 실패했습니다."
            if last_err:
                error_message += f" 마지막 오류: {last_err}"  # str(last_err)로 변환하여 메시지 포함
            self.logger.error(error_message)
            raise RuntimeError(error_message)  # 더 구체적인 RuntimeError 발생

        # 응답 파싱 및 유효성 검사
        try:
            # response.parsed가 Pydantic DTO로 직접 파싱해주는 경우
            # Google GenAI SDK에서 response_schema를 전달했을 때 이 동작을 기대할 수 있음
            parsed: Preferential = response.parsed

            # 파싱된 데이터의 유효성을 추가로 검증하고 로깅 (선택 사항)
            if not isinstance(parsed, Preferential):
                raise TypeError(f"AI 응답이 예상된 Preferential DTO 타입이 아닙니다. 실제 타입: {type(parsed)}")

            self.logger.info("상품 하나 전처리 완료 (응답 파싱 성공)")

            # 추가적인 정보 로깅
            if parsed and hasattr(parsed, 'combination'):
                combinations_count = len(parsed.combination)
                self.logger.info(f"파싱된 조합 수: {combinations_count}개")
            else:
                self.logger.warning("파싱된 응답에 'combination' 필드가 없거나 비어 있습니다.")

            return parsed
        except AttributeError as e:
            self.logger.error(f"응답 객체에 'parsed' 속성이 없거나 접근 오류: {e}")
            raise ValueError(f"AI 응답 파싱 실패 (parsed 속성 없음): {e}") from e
        except Exception as e:
            # 파싱 또는 유효성 검사 중 발생하는 모든 예외
            self.logger.error(
                f"API 응답 파싱 또는 DTO 유효성 검사 실패: {e}. 원본 응답: {response.text[:500] if hasattr(response, 'text') else 'N/A'}")
            raise ValueError(f"API 응답 파싱 실패: {e}") from e