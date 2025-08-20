import os

from dotenv import load_dotenv
from openai import OpenAI

from src.app.dto.response.response_ai_dto import response_ai_dto

load_dotenv()
api_key = os.getenv("GPT_API_KEY")

client = OpenAI(api_key=api_key)

response = client.responses.parse(model="gpt-5",
                                   input="적당히 값을 채워봐",
                                  text_format=response_ai_dto
                                   )
print(response.output_parsed)
