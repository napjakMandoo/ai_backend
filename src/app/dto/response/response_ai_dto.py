from pydantic import BaseModel
from typing import List

class monthly_plan_dto(BaseModel):
    month: int
    payment: int # 해당 월 납입금액
    total_interest: int # 해당 월 납입 금액

class timeline_dto(BaseModel):
    month: int #
    total_monthly_payment:int # 해당 월 총 납입 금액
    active_product_count:int #  해당 월 활성 상품 개수
    cumulative_interest:int # 누적 세후 이자
    cumulative_payment:int # 누적 삽입 금액

class product_dto(BaseModel):
    uuid: str
    type: str
    bank_name: str
    base_rate: float
    max_rate: float
    product_name: str
    product_max_rate: float
    product_base_rate: float
    start_month: int # 해당 월 시작 월(1-base)
    end_month: int # 해당 상품 종료 월
    allocated_amount: int # 해당 상품에 할당된 총 금액
    monthly_plan: List[monthly_plan_dto]

class combination_dto(BaseModel):
    combination_id: str
    expected_rate: float
    expected_interest_after_tax: int
    product: List[product_dto]
    timeline: List[timeline_dto]

class response_ai_dto(BaseModel):
    total_payment: int
    period_months: int
    combination: List[combination_dto]