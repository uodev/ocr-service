import uuid
import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import OCRRequest, OCRResponse
from app.services.ocr_service import OCREngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OCR Service", version="1.0.0")

# Lazy initialization for OCR Engine (EasyOCR model loading takes time)
_ocr_service = None

def get_ocr_service():
    global _ocr_service
    if _ocr_service is None:
        logger.info("Initializing OCR Engine...")
        _ocr_service = OCREngine()
        logger.info("OCR Engine initialized successfully")
    return _ocr_service

UPLOAD_DIR = "storage"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Ensure storage directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mock DB (use Redis or real DB in production)
db = {}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ocr-service"}


@app.post("/file-upload")
async def upload(file: UploadFile = File(...)):
    # Validate
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except IOError as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
        
    db[file_id] = file_path
    logger.info(f"File uploaded successfully: {file_id}")
    return {"file_id": file_id}


@app.post("/ocr", response_model=OCRResponse)
async def run_ocr(req: OCRRequest):
    file_path = db.get(req.file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File no longer exists on disk")
    
    try:
        ocr_service = get_ocr_service()
        raw, result = ocr_service.process(req.ocr, file_path, req.fields)
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
    
    return {
        "file_id": req.file_id,
        "ocr": req.ocr,
        "result": result,
        "raw_ocr": raw
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    import os

    load_dotenv()
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)