import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.ai.preprocessing.jsonSchema import Preferential

class LlmUtil:
    def __init__(self):
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
            " \"product_maximum_amount\": Refers to the maximum amount that can be deposited into the financial product.\n"
            " \"product_sub_target\": Refers to the eligible audience or conditions for subscribing to the financial product. It must be summarized so that the text does not exceed 300 characters.\n"
            " \"product_sub_amount\": Refers to the amount required to subscribe to the financial product.\n"
            " \"product_sub_way\": Refers to the methods for subscribing to the financial product. For example: 'KB스타뱅킹', '인터넷 뱅킹', '고객센터'\n"
            " \"product_sub_term\": Refers to the subscription period of the financial product. For example: '1개월 이상 36개월 이하(월단위)'\n"
            " \"product_tax_benefit\": Refers to the tax benefits of the financial product.\n"
            " \"product_preferential_info\": Refers to the description of the financial product’s preferential interest rates. It must be summarized so that the text does not exceed 1,000 characters.\n"
            " \"product_minimum_amount\": Refers to the minimum amount that can be deposited into the financial product.\n"
            " \"product_maximum_amount_per_day\": Refers to the maximum amount that can be deposited into the financial product per day.\n"
            " \"product_minimum_amount_per_day\": Refers to the minimum amount that can be deposited into the financial product per day.\n"
            " \"product_maximum_amount_per_month\": Refers to the maximum amount that can be deposited into the financial product per month.\n"
            " \"product_minimum_amount_per_month\": Refers to the minimum amount that can be deposited into the financial product per month.\n"
            
            " \"preferential_conditions_detail_header\": Refers to the title of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_detail\": Refers to the detailed information of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_interest_rate\": Refers to the interest rate of each preferential condition within the financial product.\n"
            " \"preferential_conditions_detail_keyword\": Select the appropriate keyword for each preferential condition within the financial product. The keywords must be selected from the following: [‘자동이체’, ‘비대면가입’, ‘마케팅동의’, ‘신규고객’, ‘급여이체’, ‘신용카드이용/카드실적’, ‘나이’, ‘첫거래’, ‘계좌보유’, ‘연계상품가입’, ‘장기거래/장기상품’, ‘목표금액달성/적금성공’]. If none apply, label it ‘기타’.\n"
            
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

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        try:
            return Preferential.model_validate_json(response.text)
        except ValueError as e:
            return ValueError(f"LLM response does not match schema {e}")
