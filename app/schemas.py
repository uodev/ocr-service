from pydantic import BaseModel, Field
from typing import Dict, Any, Union, List

# Field can be:
# - str: type or description (e.g., "string", "10-digit tax number")
# - dict: detailed format (e.g., {"name": "Tax ID", "type": "integer", "description": "..."})
FieldValue = Union[str, Dict[str, Any]]

# Fields can be:
# - dict with string or detailed values
# - list of field names (e.g., ["tax_id", "company_name"])
FieldsType = Union[Dict[str, FieldValue], List[str]]


class OCRRequest(BaseModel):
    file_id: str
    ocr: str = Field(..., pattern="^(easyocr|llm_ocr)$")
    fields: FieldsType


class OCRResponse(BaseModel):
    file_id: str
    ocr: str
    result: Dict[str, Any]
    raw_ocr: str