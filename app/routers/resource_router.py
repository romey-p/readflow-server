import traceback
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.db import get_db
from app.services.resource_service import resource_service
from app.services.speech_service import speech_service
from app.crud.resource_crud import resource_crud
from app.schemas.resource_schema import ResourceInfoResponse, ResourceCoordinateResponse

router = APIRouter(prefix="/api/resources", tags=["Resources"])

ALLOWED_MIME_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "application/pdf": "pdf"
}

def generate_audio(resource_id: str, analyzed_sentences: List[Dict[str, Any]], db: Database):
    try:
        print(f"[Resource: {resource_id}] 가변 속도 음성 합성 시작")
        audio_bytes, timestamps, speaking_rates = speech_service.synthesize_adaptive_audio(analyzed_sentences)
        
        audio_url = resource_service.upload_audio(audio_bytes)
        duration_seconds = timestamps[-1]["time_seconds"] if timestamps else 0.0
        
        success = resource_crud.update_audio_output(
            db=db,
            resource_id=resource_id,
            audio_url=audio_url,
            speaking_rate=speaking_rates,
            duration_seconds=duration_seconds,
            timestamps=timestamps
        )
        if success:
            print(f"[Resource: {resource_id}] 가변 배속 오디오 파이프라인 연동 완료")
        else:
            print(f"[Resource: {resource_id}] 오디오 URL DB 저장 실패")
            
    except Exception as e:
        print(f"백그라운드 오디오 생성 중 에러 발생: {traceback.format_exc()}")

@router.post("")
async def process_resource(
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Form(None, description="요청 사용자 ID (비로그인 시 생략 가능)"),
    file: UploadFile = File(..., description="업로드 지문 이미지"),
    db: Database = Depends(get_db)
):

    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="허용하지 않는 파일 형식입니다. PNG, JPG, JPEG, PDF 파일만 업로드할 수 있습니다."
        )
        
    file_bytes = await file.read()
    resource_id = str(ObjectId())
    current_time = datetime.now(timezone.utc)

    resolved_user_id = user_id.strip() if (user_id and user_id.strip()) else "guest"
    
    try:
        image_url, vlm_res, analyzed_sentences = resource_service.process_text_extraction_and_analysis(
            file_bytes=file_bytes, 
            mime_type=file.content_type
        )

        audio_url, timestamps, duration_seconds, speaking_rates = resource_service.process_audio_synthesis(analyzed_sentences)
        
        resource_crud.create_resource(
            db=db, 
            resource_id=resource_id, 
            user_id=resolved_user_id, 
            image_url=image_url, 
            vlm_res=vlm_res,
            analyzed_sentences=analyzed_sentences,
            audio_url=audio_url,
            timestamps=timestamps,
            speaking_rate=speaking_rates,
            duration_seconds=duration_seconds
        )
        
        return {
            "success": True,
            "resource_id": resource_id,
            "user_id": resolved_user_id,
            "extracted_text": vlm_res.get("extracted_text"),
            "sentences_count": len(analyzed_sentences),
            "audio_url": audio_url,
            "created_at": current_time.isoformat()
        }
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        print(f"리소스 프로세싱 실패: \n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"리소스 처리 중 에러 발생: {str(e)}")
    
@router.get("/{resource_id}", response_model=ResourceInfoResponse)
def get_resource_info(resource_id: str, db: Database = Depends(get_db)):
    result = resource_service.get_resource_info(db, resource_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 리소스를 데이터베이스에서 찾을 수 없습니다.")
    return result

@router.get("/{resource_id}/coordinates", response_model=ResourceCoordinateResponse)
def get_resource_coordinates(resource_id: str, db: Database = Depends(get_db)):
    result = resource_service.get_resource_coordinates(db, resource_id)
    if result is None:
        raise HTTPException(status_code=404, detail="해당 리소스를 데이터베이스에서 찾을 수 없습니다.")
    return result