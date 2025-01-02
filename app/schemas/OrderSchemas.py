from pydantic import BaseModel,Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.JsonSchema, handler) -> Dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema.update(type="string")
        return json_schema

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class Medicine(BaseModel):
    name: str
    mrp: float
    qty: int


class Order(BaseModel):
    date: Optional[str] = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d"))
    patient_name: str
    mobile_no: str
    address: str
    pincode: str
    medicines: List[Medicine]
    shipping_charges: float
    amount: float
    discount: float
    total_amount: float
    enquiry_made_on: Optional[str] = None
    payment_made_on: Optional[str] = None
    mode_of_payment: Optional[str] = None
    payment_reconciliation_status: Optional[str] = None
    dispatch_status: Optional[str] = None
    received_status: Optional[str] = None
    through: Optional[str] = None
    awb_docket_no: Optional[str] = None
    missing_product_during_dispatch: Optional[str] = None
    remarks: Optional[str] = None