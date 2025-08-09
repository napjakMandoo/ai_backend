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
    maximum_amount: int
    minimum_amount: int
    maximum_amount_per_month: int
    minimum_amount_per_month: int
    maximum_amount_per_day: int
    minimum_amount_per_day: int
    tax_benefit: str
    preferential_info: str
    sub_amount: str
    sub_term: str
    product_period: List[product_period_dto]

class ai_payload_dto(BaseModel):
    tax_rate: float
    products: List[product_dto]
