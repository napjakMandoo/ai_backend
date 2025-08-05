import logging
import os
import time
import random

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

    def create_preferential_json(self, content:str)-> Preferential | ValueError:
        SYS_RULE = (
            "## BASE ROLES\n"
            "- Must output JSON only. The results you provide will be stored in database tables. Below are the instructions for each value.\n"
            " \"product_name\": It refers to the name of the financial product.\n"
            " \"product_basic_rate\":  Refers to the highest base interest rate of the financial product. For example, if product A offers 2.1% for maturities of 6 to under 9 months and 3.0% for maturities of 9 to under 12 months, then it should return 3.0%.\n"
            " \"product_max_rate\": Refers to the sum of the product’s highest base interest rate and all applicable preferential rates—that is, the optimal interest rate when all conditions are met.\n"
            " \"product_type\": Refers to the type of the financial product. Returns 'deposit' for deposit products and 'savings' for savings products.\n"
            " \"product_url_link\": Refers to the URL of the financial product.\n"
            " \"product_maximum_amount\": The maximum amount that can be deposited in this financial product must be specified; if no limit exists, return –1.\n"
            " \"product_sub_target\": Refers to the eligible audience or conditions for subscribing to the financial product. It must be summarized so that the text does not exceed 300 characters.\n"
            " \"product_sub_amount\": Refers to the amount required to subscribe to the financial product.\n"
            " \"product_sub_way\": Refers to the methods for subscribing to the financial product. For example: 'KB스타뱅킹', '인터넷 뱅킹', '고객센터'\n"
            " \"product_sub_term\": Refers to the subscription period of the financial product. For example: '1개월 이상 36개월 이하(월단위)'\n"
            " \"product_tax_benefit\": Refers to the tax benefits of the financial product.\n"
            " \"product_preferential_info\": Refers to the description of the financial product’s preferential interest rates. It must be summarized so that the text does not exceed 1,000 characters.\n"
            " \"product_minimum_amount\": Refers to the minimum amount that can be deposited into the financial product.\n"
            " \"product_maximum_amount_per_day\": You must specify the maximum amount that can be deposited in this financial product per day; if there is no daily limit, return –1.\n"
            " \"product_minimum_amount_per_day\": Refers to the minimum amount that can be deposited into the financial product per day.\n"
            " \"product_maximum_amount_per_month\": You must specify the maximum amount that can be deposited in this financial product per month; if there is no monthly limit, return –1.\n"
            " \"product_minimum_amount_per_month\": Refers to the minimum amount that can be deposited into the financial product per month.\n"
            
            " \"preferential_conditions_detail_header\": Refers to the title of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_detail\": Refers to the detailed information of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_interest_rate\": Refers to the interest rate of each preferential condition within the financial product.\n"
            # " \"preferential_conditions_detail_keyword\": Select the appropriate keyword for each preferential condition within the financial product. The keywords must be selected from the following: ['ACCOUNT_HOLDING','AGE','AUTOMATIC_TRANSFER','CREDIT_CARD_USE_OR_PERFORMANCE','FIRST_TRANSACTION','LINKED_PRODUCT_JOIN','LONG_TERM_TRANSACTION_OR_PRODUCT','MARKETING_CONSENT','NEW_CUSTOMER','NON_FACE_TO_FACE_JOIN','SALARY_TRANSFER','TARGET_AMOUNT_ACHIEVED_OR_SAVE_SUCCESS']. If none apply, label it ‘기타’.\n"
            " \"preferential_conditions_detail_keyword\": Select an appropriate keyword for each preferential condition within the financial product. "
            " The keyword must be chosen from the following list: ['ACCOUNT_HOLDING','AGE','AUTOMATIC_TRANSFER','CREDIT_CARD_USE_OR_PERFORMANCE','FIRST_TRANSACTION','LINKED_PRODUCT_JOIN','LONG_TERM_TRANSACTION_OR_PRODUCT','MARKETING_CONSENT','NEW_CUSTOMER','NON_FACE_TO_FACE_JOIN','SALARY_TRANSFER','TARGET_AMOUNT_ACHIEVED_OR_SAVE_SUCCESS']"
            ".If no suitable keyword applies, label it as 'ETC' In other words, each preferential condition must map to exactly one keyword.\n"
            "\"product_period_period\": Indicates the deposit term for the financial product. Examples are as follows:\n"
            "1. If \"3 months or more and up to 6 months,\" then \"[3,6]\"\n"
            "2. If \"up to 3 months,\" then \"[-,3]\"\n"
            "3. If \"60 months or more,\" then \"[60, -]\"\n"
            "4. If it is \"12 months\", then [12, 12]\n"
            " \"product_period_basic_rate\": Indicates the interest rate corresponding to the deposit term for the financial product.\n"
            "Alright, those are all the instructions. Next up is the information.\n\n"
            "## INFORMATION\n"
        )

        prompt = f"{SYS_RULE}{content}"

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Preferential,
        )

        self.logger.info("상품 하나 전처리 시작")
        max_retry = 6  # 10회 → 6회로 축소(지수 백오프 한계 ≈ 2분)
        for attempt in range(1, max_retry + 1):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                break  # 성공 → 즉시 탈출
            except ServerError as e:
                # 503 (과부하)만 잡아서 재시도, 그 외 오류는 즉시 전파
                if getattr(e, "status_code", None) == 503:
                    wait = min(60, 2 ** (attempt - 1)) + random.random()  # 캡 60s + 지터
                    self.logger.warning(
                        f"[503] 모델 과부하: {attempt}/{max_retry}회차 재시도 → {wait:.1f}s 대기"
                    )
                    time.sleep(wait)
                    continue
                raise

        else:
            # flash 모델 6회 모두 실패 → 더 안정적인 모델로 1회 페일오버
            self.logger.warning("gemini-2.5-flash 6회 실패, gemini-pro로 전환")
            response = self.client.models.generate_content(
                model="gemini-pro",
                contents=prompt,
                config=config,
            )

        parsed: Preferential = response.parsed
        self.logger.info("상품 하나 전처리 끝")
        return parsed

