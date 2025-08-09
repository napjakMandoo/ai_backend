from pydantic import BaseModel
from typing import List

class monthly_plan_dto(BaseModel):
    month: int
    payment: int
    total_interest: int

class product_dto(BaseModel):
    uuid: str
    start_month: int
    end_month: int
    monthly_plan: List[monthly_plan_dto]

class combination_dto(BaseModel):
    combination_id: str
    expected_rate: float                # "6.00" 문자열도 float으로 파싱됩니다.
    expected_interest_after_tax: int
    product: List[product_dto]

class response_ai_dto(BaseModel):
    total_payment: int
    period_months: int
    combination: List[combination_dto]