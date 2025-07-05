from pydantic import BaseModel
# from pydantic import constr
from typing import Literal


Keyword = Literal["자동이체", "비대면가입", "마케팅동의", "신규고객", "급여이체", "신용카드이용/카드실적", "나이", "첫거래", "계좌보유", "연계상품가입", "장기거래/장기상품", "목표금액달성/적금성공"]

class Preferential(BaseModel):
    header:str# 우대조건 제목
    detail:list[str] # 우대조건 더보기 정보
    interest_rate:float # 우대조건 금리
    keywords:Keyword # 우대조건 키워드