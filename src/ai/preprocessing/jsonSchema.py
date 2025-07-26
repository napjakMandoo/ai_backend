from pydantic import BaseModel
from typing import Literal


Keyword = Literal["자동이체", "비대면가입", "마케팅동의", "신규고객", "급여이체", "신용카드이용/카드실적",
                  "나이", "첫거래", "계좌보유", "연계상품가입", "장기거래/장기상품", "목표금액달성/적금성공", "기타"]

class Preferential(BaseModel):
    product_name: str # 상품: 상품명
    product_max_rate: float #  상품: 최대 금리
    product_type: str # 상품: 적금(deposit), 예금(savings)
    product_info: list[str] # 상품: 상품 안내
    product_interest_rates: list[str] # 상품: 금리 정보
    product_emergency_withdrawal: list[str]  # 상품: 긴급출금 및 해지 안내
    product_terms_conditions:list[str]  # 상품: 상품 설명서 및 이용약관
    product_url_links: str # 상품: 통장 개설 URL
    product_maximum_amount: int # 상품: 최대금액
    product_minimum_amount: int # 상품: 최소금액
    product_maximum_amount_per_day: int # 상품: 하루 최대 금액
    product_minimum_amount_per_day: int # 상품 : 하루 최소 금액

    product_period_period: list[str] # 상품별 기간: 예치 기간
    product_period_base_rate: list[float] # 상품별 기간: 기간별 기본 금리

    preferential_conditions_detail_header: list[str] # 우대조건 상세정보: 각 우대조건 제목
    preferential_conditions_detail_detail: list[str] # 우대조건 상세정보: 각 우대조건 더보기 정보
    preferential_conditions_detail_interest_rate: list[float] # 우대조건 상세정보: 각 우대조건 금리
    preferential_conditions_detail_keyword: list[str] # 우대조건 상세정보: 각 우대조건 키워드
