from pydantic import BaseModel, Field
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

class User(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: str
    full_name: str
    disabled: bool = False
    hashed_password: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        extra = "allow"  # Allow extra fields in the request payload