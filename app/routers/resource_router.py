from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

from app.core.db import get_db
from app.services.resource_service import resource_service
from app.crud.resource_crud import resource_crud

router = APIRouter(prefix="/api/resources", tags=["Resources"])

ALLOWED_MIME_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "application/pdf": "pdf"
}

@router.post("")
async def process_image_resource(
    user_id: str = Form(..., description="요청 사용자 ID"),
    file: UploadFile = File(..., description="업로드 지문 이미지"),
    db: Database = Depends(get_db)
):

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="허용하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF 파일만 업로드할 수 있습니다."
        )
        
    file_bytes = await file.read()
    resource_id = str(ObjectId())
    current_time = datetime.now(timezone.utc)
    
    try:
        cloudinary_url = resource_service.upload_image(file_bytes, folder="readflow/images")
        vlm_res = resource_service.extract_layout(file_bytes, file.content_type)
        
        resource_crud.create_resource(
            db=db, 
            resource_id=resource_id, 
            user_id=user_id, 
            cloudinary_url=cloudinary_url, 
            vlm_res=vlm_res
        )
        
        return {
            "success": True,
            "resource_id": resource_id,
            "extracted_text": vlm_res.get("extracted_text"),
            "created_at": current_time.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 처리 중 에러 발생: {str(e)}")