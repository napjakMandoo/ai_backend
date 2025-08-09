from pydantic import BaseModel
from typing import List

class monthly_plan_dto(BaseModel):
    month: int
    payment: int
    total_interest: int

class product_dto(BaseModel):
    product_uuid: str
    bank_name: str
    product_name: str
    product_max_rate: float
    product_base_rate: float
    start_month: int
    end_month: int
    monthly_plan: List[monthly_plan_dto]

class combo_dto(BaseModel):
    combination_id: str
    expected_rate: float
    expected_interest_after_tax: int
    product: List[product_dto]

class response_front_dto(BaseModel):
    total_payment: int
    period_months: int
    combo: List[combo_dto]
