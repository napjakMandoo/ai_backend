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
from google.genai.errors import ServerError

from src.shared.ai.jsonSchema import Preferential

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
        """
        Preferential(Pydantic 모델)을 JSON 파일로 저장.
        - out_dir: 저장 디렉터리
        - filename: 파일명(확장자 제외). 없으면 product_name+타임스탬프 기반 자동 생성
        - by_alias: alias 키 사용 여부
        - pretty: 들여쓰기 여부
        """
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

    def create_preferential_json(self, content:str)-> Preferential | ValueError:
        SYS_RULE = (
            "## BASE ROLES\n"
            "- Must output JSON only. The results you provide will be stored in database tables.\n"
            "- All percentage values must be numbers without '%' (e.g., '3.65%' → 3.65).\n"
            "- All amounts and periods must be numbers. Use -1 to indicate 'no limit' or 'not specified'.\n"
            "- All arrays for related fields must be the same length and aligned by index.\n\n"

            "\"product_name\": The name of the financial product.\n"
            "\"product_basic_rate\": Highest base interest rate across all eligible terms.\n"
            "\"product_max_rate\": Sum of the product's highest base interest rate and all preferential rates (optimal case).\n"
            "\"product_type\": 'deposit' for deposits, 'savings' for savings products.\n"
            "\"product_url_link\": URL of the financial product.\n"
            "\"product_maximum_amount\": Maximum deposit amount. Use -1 if no limit or not specified.\n"
            "\"product_sub_target\": Eligible audience/conditions, summarized to ≤300 characters.\n"
            "\"product_sub_amount\": Required amount for subscription.\n"
            "\"product_sub_way\": Methods to subscribe (e.g., 'KB스타뱅킹', '인터넷 뱅킹').\n"
            "\"product_sub_term\": Subscription period (e.g., '1개월 이상 36개월 이하(월단위)').\n"
            "\"product_tax_benefit\": Tax benefits of the product.\n"
            "\"product_preferential_info\": Summary of preferential rates, ≤1000 characters.\n"
            "\"product_minimum_amount\": Minimum deposit amount. Use -1 if not specified.\n"
            "\"product_maximum_amount_per_day\": Maximum daily deposit amount. Use -1 if no limit or not specified.\n"
            "\"product_minimum_amount_per_day\": Minimum daily deposit amount. Use -1 if not specified.\n"
            "\"product_maximum_amount_per_month\": Maximum monthly deposit amount. Use -1 if no limit or not specified.\n"
            "\"product_minimum_amount_per_month\": Minimum monthly deposit amount. Use -1 if not specified.\n\n"

            " \"preferential_conditions_detail_header\": Refers to the title of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_detail\": Refers to the detailed information of each preferential condition within the financial product. And it must be a maximum of 250 characters.\n"
            " \"preferential_conditions_detail_interest_rate\": Refers to the interest rate of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_keyword\": Select an appropriate keyword for each preferential condition within the financial product. "
            " The keyword must be chosen from the following list: ['ACCOUNT_HOLDING','AGE','AUTOMATIC_TRANSFER','CREDIT_CARD_USE_OR_PERFORMANCE','FIRST_TRANSACTION','LINKED_PRODUCT_JOIN','LONG_TERM_TRANSACTION_OR_PRODUCT','MARKETING_CONSENT','NEW_CUSTOMER','NON_FACE_TO_FACE_JOIN','SALARY_TRANSFER','TARGET_AMOUNT_ACHIEVED_OR_SAVE_SUCCESS']"
            ".If no suitable keyword applies, label it as 'ETC' In other words, each preferential condition must map to exactly one keyword.\n"

            "## AMOUNT NORMALIZATION RULES (APPLY BEFORE OUTPUT)\n"
            "- The following inputs MUST be normalized to -1 (meaning 'no limit' or 'not specified'):\n"
            "  * null/None, empty string, 'N/A', '-', '무제한', '제한 없음', '없음'.\n"
            "  * Any negative sentinel such as -99, -999, -9999, -99999, -999999, etc.\n"
            "  * Extremely large placeholders indicating 'unlimited', e.g., >= 9,000,000,000,000,000,000\n"
            "    (including 9223372036854775807).\n"
            "- Otherwise, keep the numeric value as-is.\n"
            "- IMPORTANT: 0 is a valid numeric value and MUST NOT be converted to -1.\n"
            "- For minimum fields: if normalized to -1, treat as 'no minimum'. For maximum fields: if normalized to -1, treat as 'no limit'.\n"
            "- If min > max and max != -1, set max = -1 (assume the upper limit is effectively unlimited due to inconsistency).\n\n"

            "## PERIOD FIELDS\n"
            "\"product_period_period\" and \"product_period_basic_rate\" MUST follow these rules:\n"
            "1) SHAPE (choose exactly one mode)\n"
            "   - Mode A (bucketed):\n"
            "     * \"product_period_period\": an array of bracketed range strings.\n"
            "       Each item is exactly: \"[min_months, max_months]\" where min_months/max_months are JSON numbers,\n"
            "       and max_months may be '-' for open-ended.\n"
            "       Examples: \"[1, 5]\", \"[6, 11]\", \"[12, 23]\", \"[24, 35]\", \"[36, 60]\", \"[60, -]\"\n"
            "     * \"product_period_basic_rate\": number array, SAME LENGTH as \"product_period_period\".\n"
            "   - Mode B (single range):\n"
            "     * \"product_period_period\": a SINGLE bracketed range string, e.g. \"[12, 12]\", \"[12, -]\", \"[1, 36]\"\n"
            "     * \"product_period_basic_rate\": a SINGLE number (length = 1)\n\n"

            "2) ABSOLUTE PROHIBITIONS:\n"
            "   - Do NOT output natural language in periods. NEVER write things like \"1년이상\", \"3년제\", \"12개월\".\n"
            "   - Do NOT output plain numbers or quoted numbers in periods like \"12\", \"36\".\n"
            "   - NEVER output without square brackets. For example, \"12, 12\" is INVALID — it must be \"[12, 12]\".\n"
            "   - Period items must be bracketed range strings ONLY (e.g., \"[12, 12]\"), not JSON arrays like [12,12], and not bare strings like \"12\".\n"
            "   - Percent signs are forbidden in rates. Use numbers only (e.g., 3.65 not \"3.65%\").\n\n"

            "3) NORMALIZATION RULES (for periods):\n"
            "   Convert any natural-language period to bracketed months:\n"
            "   - \"N개월\" (exact)               → \"[N, N]\"\n"
            "   - \"N개월 이상\"                  → \"[N, -]\"\n"
            "   - \"N개월 이하\" / \"최대 N개월\"   → \"[0, N]\"\n"
            "   - \"N~M개월\" / \"N개월 이상 M개월 이하\" → \"[N, M]\"\n"
            "   - \"N년\" (exact)                 → \"[12*N, 12*N]\"\n"
            "   - \"N년 이상\"                    → \"[12*N, -]\"\n"
            "   - \"N년 이하\"                    → \"[0, 12*N]\"\n"
            "   - \"N~M년\"                       → \"[12*N, 12*M]\"\n"
            "   - \"N년제\"                       → \"[12*N, 12*N]\"\n"
            "   - \"1년\" is \"[12, 12]\"; \"3년이상\" is \"[36, -]\"\n\n"

            "4) SELF-CORRECTION RULES:\n"
            "   - If you produced two plain numbers like [\"12\",\"36\"] with ONE rate, MERGE them into a single range string: \"[12, 36]\" (Mode B).\n"
            "   - If you produced a list of natural-language labels, REPLACE ALL with properly bracketed range strings per the normalization rules.\n"
            "   - If you produced a value like \"12, 12\" (missing brackets), FIX it to \"[12, 12]\" before final output.\n"
            "   - If lengths mismatch between periods and rates in Mode A, either:\n"
            "       a) split/merge ranges so counts match, or\n"
            "       b) fallback to Mode B with a single merged range and a single rate.\n"
            "   - Never output invalid shapes. If information is insufficient to build multiple buckets, use Mode B.\n\n"

            "5) FORMAT GUARANTEE:\n"
            "   - Every item in \"product_period_period\" MUST match this regex exactly:\n"
            "     ^\\[\\s*(\\d+|-)\\s*,\\s*(\\d+|-)\\s*\\]$\n"
            "   - If any item fails this regex, FIX IT before output.\n\n"

            "6) EXAMPLES:\n"
            "   - Ideal bucketed (Mode A):\n"
            "     \"product_period_period\": [\"[1, 5]\",\"[6, 11]\",\"[12, 23]\",\"[24, 35]\",\"[36, 60]\"],\n"
            "     \"product_period_basic_rate\": [1.5,1.85,2.0,1.7,1.7]\n"
            "   - From natural language (normalize):\n"
            "     Input like [\"1년이상\",\"3년제\"] → \"product_period_period\": [\"[12, -]\",\"[36, 36]\"]\n"
            "   - Two numbers + one rate:\n"
            "     Input like [\"12\",\"36\"] with [1.9] → \"product_period_period\": \"[12, 36]\", \"product_period_basic_rate\": [1.9]\n\n"

            "Alright, those are all the instructions. Next up is the information.\n\n"
            "## INFORMATION\n"
        )

        prompt = f"{SYS_RULE}{content}"

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Preferential,
        )

        self.logger.info("상품 하나 전처리 시작")
        max_retry = 6
        for attempt in range(1, max_retry + 1):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                break
            except ServerError as e:
                if getattr(e, "status_code", None) == 503:
                    wait = min(60, 2 ** (attempt - 1)) + random.random()  # 캡 60s + 지터
                    self.logger.warning(
                        f"[503] 모델 과부하: {attempt}/{max_retry}회차 재시도 → {wait:.1f}s 대기"
                    )
                    time.sleep(wait)
                    continue
                raise

        else:
            self.logger.warning("gemini-2.5-flash 6회 실패, gemini-pro로 전환")
            response = self.client.models.generate_content(
                model="gemini-pro",
                contents=prompt,
                config=config,
            )

        parsed: Preferential = response.parsed
        self.logger.info("상품 하나 전처리 끝")

        try:
            self.save_preferential_to_json(
                obj=parsed,
                out_dir="./data/preferential",  # 예시 경로
                by_alias=True,
                pretty=True,
            )
        except Exception as e:
            self.logger.warning(f"JSON 저장 실패: {e}")

        return parsed

