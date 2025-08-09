from pydantic import BaseModel, ValidationError
from enum import Enum

class Period(str, Enum):
    SHORT = "SHORT"
    MID = "MID"
    LONG = "LONG"


class request_combo_dto(BaseModel):
    amount: int
    period: Period
