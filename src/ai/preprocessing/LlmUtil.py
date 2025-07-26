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
            "- \"product_name\": This refers to the name of each deposit and savings product.\n"
            " \"product_max_rate\" is the maximum interest rate when all preferential conditions and the maximum basic interest rate for each product are considered.\n"
            " \"product_type\", return 'savings' if the product is a deposit, and 'deposit' if it's a savings product.\n"
            "\"product_interest_rates\" should represent each of the interest rate details\n."
            "\"product_emergency_withdrawal\" is a value used to explain \"Guidance on Emergency Withdrawal and Termination.\"\n"
            "\"product_terms_conditions\" is a value used to describe the product manual and terms of service.\n"
            "\"product_url_links\" is a value that represents the product URL.\n"
            "\"product_maximum_amount\" is the maximum amount that can be deposited into a product. If there's a specified maximum daily deposit amount and a maximum deposit period, please calculate and return the total maximum amount.\n"
            "\"product_maximum_amount\" is the maximum amount that can be deposited into the product. If not specified, return 50,000,000 KRW.\n"
            "\"product_maximum_amount_per_day\" is the minimum amount that can be deposited per day."
            "\"product_minimum_amount_per_day\" is the minimum amount that can be deposited per day."
            "For \"product_period_period\", please return the period for each product. For example, if it's '1 to 6 months', '6 to 12 months', or '12 months to indefinite', return it as '1,6', '6,12', '12,-1' respectively.\n"
            "\"product_period_period\" should represent the deposit period for the product. If it's in a \"minimum months - maximum months\" format, use the minimum number of months. For example, if the period is \"3 months - 6 months,\" specify it as \"3 months.\"\n"
            "\"product_period_base_rate\" should represent the basic interest rate applied for each period.\n"
            "\"preferential_conditions_detail_header\" should represent the title of the preferential conditions applied to each product. If the title exceeds 15 characters, please summarize it appropriately.\n"
            "\"preferential_conditions_detail_interest_rate\" refers to the interest rate of the preferential condition. If a specific preferential condition is further divided into sub-conditions, return the maximum interest rate based on those sub-conditions. For example, if there are preferential conditions 'A', 'B', and 'C', and 'C' is further divided into 'C-1' and 'C-2', then for 'C', return the maximum interest rate, formatted as [float, float, float].\n"
            "\"preferential_conditions_detail_interest_rate\" should represent the detailed information for each preferential condition.\n"
            "\"preferential_conditions_detail_keyword\" is the keyword for each preferential condition. Please match it as closely as possible to the keywords I've specified. If you determine there isn't a suitable keyword, use '기타' (Other).\n"
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
