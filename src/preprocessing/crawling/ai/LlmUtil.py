import logging
import os
import time
import random

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

from src.preprocessing.crawling.ai.jsonSchema import Preferential

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
            "1. If \"3 months or more and less than 6 months,\" then \"[3,6)\"\n"
            "2. If \"3 months or more and up to 6 months,\" then \"[3,6]\"\n"
            "3. If \"up to 3 months,\" then \"[-,3]\"\n"
            "4. If \"up to 3 months,\" then \"[-,3)\"\n"
            "5. If \"60 months or more,\" then \"[60, -]\"\n"
            "6. If \"over 60 months,\" then \"(60, -]\"\n"
            "7. If it is \"12 months\", then [12, 12]\n"
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
        try:
            max_retry = 10
            for i in range(max_retry):
                try:
                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=config,
                    )
                    break
                except ServerError as e:
                    self.logger.error(f"전처리 도중 에러 발생: {e}")
                    error_dict = e.args[0] if e.args else {}
                    if isinstance(error_dict, dict) and error_dict.get('error', {}).get('code') == 503:
                        time.sleep(2 ** i + random.random())
                        continue
                    raise

            else:
                raise RuntimeError("Gemini API 503 계속 발생")

            parsed: Preferential = response.parsed
            self.logger.info("상품 하나 전처리 끝")
            return parsed

        except ValueError as e:
            self.logger.error(f"스키마 매칭 오류: {e}")
            raise

        except Exception as e:
            self.logger.error(f"예상치 못한 오류: {e}")
            raise
