import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ai.jsonSchema import Preferential


class LlmUtil:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")

        if not api_key:
            raise RuntimeError("GENAI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key)

    def create_preferential_json(self, content:str)-> Preferential | ValueError:

        SYS_RULE = (
            "## ROLES\n"
            "- Must output JSON only\n"
            "- The `header` value is limited to a maximum of 15 characters."
            "\n"
        )

        prompt = f"{SYS_RULE} \n\n {content}"

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
