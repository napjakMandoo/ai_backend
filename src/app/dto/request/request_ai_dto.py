from pydantic import BaseModel
from typing import List

class product_period_dto(BaseModel):
    period: str          # 예: "[-,3]", "[3,6]", "[6,-]"
    basic_rate: float

class product_dto(BaseModel):
    uuid: str
    name: str
    base_rate: float
    max_rate: float
    type: str
    max_amount: int
    min_amount: int
    max_amount_per_month: int
    min_amount_per_month: int
    max_amount_per_day: int
    min_amount_per_day: int
    tax_benefit: str
    product_period: List[product_period_dto]

class ai_payload_dto(BaseModel):
    tax_rate: float
    products: List[product_dto]
