import base64
import easyocr
import json
import logging
import mimetypes
import tempfile
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pdf2image import convert_from_path
import os

load_dotenv()

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class OCREngine:
    def __init__(self):
        logger.info("Loading EasyOCR model...")
        self.reader = easyocr.Reader(['tr', 'en'], gpu=False)
        logger.info("EasyOCR model loaded")

    def process(self, method: str, file_path: str, fields: dict) -> tuple[str, dict]:
        """Process file with OCR and extract fields."""
        logger.info(f"Processing file with method: {method}")
        
        if method == "easyocr":
            raw_text = self._extract_text_with_easyocr(file_path)
            logger.info(f"Text extracted, length: {len(raw_text)} chars")
            result = self._parse_fields_with_llm(raw_text, fields)
        
        elif method == "llm_ocr":
            raw_text, result = self._process_with_vision(file_path, fields)
            logger.info(f"Vision API processed, length: {len(raw_text)} chars")
        
        else:
            raise ValueError(f"Unsupported OCR method: {method}")
        
        logger.info(f"Fields parsed: {list(result.keys())}")
        return raw_text, result

    def _is_pdf(self, file_path: str) -> bool:
        """Check if file is PDF."""
        return Path(file_path).suffix.lower() == '.pdf'

    def _convert_pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF to images."""
        logger.info(f"Converting PDF: {pdf_path}")
        try:
            images = convert_from_path(pdf_path, dpi=300)
            logger.info(f"Converted to {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise RuntimeError(f"Failed to convert PDF: {e}")

    def _extract_text_with_easyocr(self, file_path: str) -> str:
        """Extract text from image or PDF using EasyOCR."""
        try:
            if self._is_pdf(file_path):
                images = self._convert_pdf_to_images(file_path)
                all_text = []
                
                for i, image in enumerate(images):
                    logger.info(f"Processing page {i + 1}/{len(images)}")
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        image.save(tmp.name, 'PNG')
                        result = self.reader.readtext(tmp.name, detail=0)
                        all_text.extend(result)
                        os.unlink(tmp.name)
                
                return " ".join(all_text)
            else:
                result = self.reader.readtext(file_path, detail=0)
                return " ".join(result)
        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            raise RuntimeError(f"Failed to extract text: {e}")

    def _normalize_fields(self, fields) -> tuple[list[dict], list[str]]:
        """
        Normalize different field formats to a standard structure.
        Returns: (normalized_fields, original_keys)
        """
        normalized = []
        original_keys = []
        type_keywords = {"string", "integer", "int", "float", "number", "boolean", "bool", "date", "list", "array"}
        
        # Handle list format: ["field1", "field2"]
        if isinstance(fields, list):
            for key in fields:
                original_keys.append(key)
                normalized.append({
                    "key": key,
                    "name": key.replace("_", " ").title(),
                    "description": "",
                    "type": "string"
                })
            return normalized, original_keys
        
        # Handle dict formats
        for key, value in fields.items():
            original_keys.append(key)
            
            if isinstance(value, dict):
                # Detailed format
                normalized.append({
                    "key": key,
                    "name": value.get("name", key),
                    "description": value.get("description", ""),
                    "type": value.get("type", "string")
                })
            elif isinstance(value, str):
                value_lower = value.lower().strip()
                if value_lower in type_keywords:
                    # Simple type format
                    normalized.append({
                        "key": key,
                        "name": key.replace("_", " ").title(),
                        "description": "",
                        "type": value_lower
                    })
                else:
                    # Description format
                    normalized.append({
                        "key": key,
                        "name": key.replace("_", " ").title(),
                        "description": value,
                        "type": "string"
                    })
            else:
                normalized.append({
                    "key": key,
                    "name": key.replace("_", " ").title(),
                    "description": str(value) if value else "",
                    "type": "string"
                })
        
        return normalized, original_keys

    def _parse_fields_with_llm(self, text: str, fields) -> dict:
        """Parse fields from text using LLM."""
        normalized_fields, original_keys = self._normalize_fields(fields)
        
        field_descriptions = []
        for field in normalized_fields:
            desc = f'- "{field["key"]}": {field["name"]}'
            if field["type"]:
                desc += f' ({field["type"]})'
            if field["description"]:
                desc += f' - {field["description"]}'
            field_descriptions.append(desc)
        
        fields_text = "\n".join(field_descriptions)
        
        prompt = f"""You are a document data extraction assistant. Extract the requested fields from the following OCR text.

## Requested Fields:
{fields_text}

## OCR Text:
{text}

## Instructions:
1. Extract the exact values for each field from the text
2. Return the results as a JSON object with the field keys
3. If a field cannot be found, set its value to null
4. Respect the type specified for each field (convert numbers to integers/floats as needed)
5. Clean up any OCR artifacts or noise in the extracted values

Return ONLY a valid JSON object with the field keys and their extracted values."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            return {k: result.get(k) for k in original_keys}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            raise RuntimeError("Failed to parse extraction results")
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            raise RuntimeError(f"Failed to extract fields: {e}")

    def _process_with_vision(self, file_path: str, fields: dict) -> tuple[str, dict]:
        """Process image with GPT-4o Vision API."""
        
        # Convert PDF first page to image if needed
        if self._is_pdf(file_path):
            images = self._convert_pdf_to_images(file_path)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                images[0].save(tmp.name, 'PNG')
                image_path = tmp.name
                mime_type = "image/png"
        else:
            image_path = file_path
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "image/jpeg"
        
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.standard_b64encode(image_file.read()).decode("utf-8")
            
            normalized_fields, original_keys = self._normalize_fields(fields)
            field_descriptions = []
            for field in normalized_fields:
                desc = f'- "{field["key"]}": {field["name"]}'
                if field["type"]:
                    desc += f' ({field["type"]})'
                if field["description"]:
                    desc += f' - {field["description"]}'
                field_descriptions.append(desc)
            
            fields_text = "\n".join(field_descriptions)
            
            prompt = f"""You are an OCR and document data extraction assistant. Analyze this image and:

1. First, extract ALL visible text from the image (this will be the raw_text)
2. Then, extract the specific fields requested below

## Requested Fields:
{fields_text}

## Instructions:
- Return a JSON object with two keys: "raw_text" and "fields"
- "raw_text" should contain all text visible in the image, preserving the general reading order
- "fields" should contain the extracted values for each requested field key
- If a field cannot be found, set its value to null
- Respect the type specified for each field (convert numbers to integers/floats as needed)
- Clean up any noise or artifacts in the extracted values

Return ONLY a valid JSON object."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            
            raw_text = result.get("raw_text", "")
            parsed_fields = result.get("fields", {})
            
            return raw_text, {k: parsed_fields.get(k) for k in original_keys}
            
        except json.JSONDecodeError as e:
            logger.error(f"Vision API JSON parse failed: {e}")
            raise RuntimeError("Failed to parse extraction results")
        except Exception as e:
            logger.error(f"Vision API failed: {e}")
            raise RuntimeError(f"Failed to process with Vision API: {e}")
        finally:
            # Clean up temp file
            if self._is_pdf(file_path) and 'image_path' in locals():
                try:
                    os.unlink(image_path)
                except:
                    pass