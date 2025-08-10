from pydantic import BaseModel
from typing import Literal

class Preferential(BaseModel):
    product_name: str # 상품: 상품명
    product_basic_rate: float # 상품: 기본 금리
    product_max_rate: float #  상품: 최대 금리
    product_type: str # 상품: 적금(deposit), 예금(savings)
    product_url_links: str # 상품: 통장 개설 URL
    product_info: list[str] # 상품: 상품 안내
    product_maximum_amount: int # 상품: 최대금액
    product_minimum_amount: int # 상품: 최소금액
    product_maximum_amount_per_day: int # 상품: 하루 최대 금액
    product_minimum_amount_per_day: int # 상품 : 하루 최소 금액
    product_maximum_amount_per_month: int # 상품: 한달 최대 금액
    product_minimum_amount_per_month: int # 상품 : 한달 최소 금액
    product_sub_target: str # 상품: 가입 대상
    product_sub_amount: str  # 상품: 가입 금액
    product_sub_way:str  # 상품: 가입 방법
    product_sub_term:str  # 상품: 가입 기간
    product_tax_benefit:str  # 상품: 세제 혜택
    product_preferential_info:str  # 상품: 우대조건 총 취

    preferential_conditions_detail_header: list[str] # 우대조건 상세정보: 각 우대조건 제목
    preferential_conditions_detail_detail: list[str] # 우대조건 상세정보: 각 우대조건 더보기 정보
    preferential_conditions_detail_interest_rate: list[float] # 우대조건 상세정보: 각 우대조건 금리
    preferential_conditions_detail_keyword: list[str] # 우대조건 상세정보: 각 우대조건 키워드

    product_period_period: list[str] # 상품별 기간: 예치 기간
    product_period_base_rate: list[float] # 상품별 기간: 기간별 기본 금리

